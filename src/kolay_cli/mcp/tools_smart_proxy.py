"""Smart Proxy MCP tools — filtered search, aggregation, and cache diagnostics.

These tools sit between the LLM and the raw Kolay IK API, enforcing:
  - In-memory TTL caching  (no API spam)
  - Server-side projection (minimal JSON payloads)
  - Hard-limit truncation  (context-window safety + self-correction hint)
  - Zero-data math         (LLM never sees raw rows for stats)
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastmcp.tools import Tool

from ..security import require_auth
from ..ttl_cache import fetch_all_employees, cache_status


# ---------------------------------------------------------------------------
# Helper: project (whitelist) fields from a list of dicts
# ---------------------------------------------------------------------------

def _project(items: list[dict[str, Any]], fields: list[str]) -> list[dict[str, Any]]:
    """Strip all keys not present in *fields* from each item."""
    return [{k: item[k] for k in fields if k in item} for item in items]


# ---------------------------------------------------------------------------
# Tool 1: search_employees
# ---------------------------------------------------------------------------

@require_auth
def search_employees(
    department: str | None = None,
    birth_month: int | None = None,
    fields: list[str] | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """[READ] Smart employee search with server-side filtering, projection, and truncation.

    Reads from a 5-minute in-memory cache (avoids spamming the Kolay API).

    Args:
        department: Filter by department name (case-insensitive substring match).
        birth_month: Filter by birth month (1-12).
        fields: Whitelist of fields to return per employee (e.g. ["id", "firstName", "lastName", "department"]).
                If omitted, returns a default slim projection.
        limit: Max results to return (hard-capped at 50).

    Returns:
        {results: [...], count: int, total_before_limit: int, _meta: {...}}
    """
    all_employees = fetch_all_employees()
    filtered = list(all_employees)

    # ── In-memory filters ─────────────────────────────────────────────
    if department:
        dept_lower = department.lower()
        filtered = [
            e for e in filtered
            if dept_lower in (e.get("department") or "").lower()
        ]

    if birth_month is not None:
        def _matches_month(emp: dict[str, Any]) -> bool:
            bd = emp.get("birthDate") or ""
            try:
                return datetime.fromisoformat(bd[:10]).month == birth_month
            except (ValueError, TypeError):
                return False
        filtered = [e for e in filtered if _matches_month(e)]

    total_before_limit = len(filtered)

    # ── Hard-cap at 50 ────────────────────────────────────────────────
    effective_limit = min(limit, 50)
    truncated = total_before_limit > effective_limit
    filtered = filtered[:effective_limit]

    # ── Projection ────────────────────────────────────────────────────
    default_fields = ["id", "firstName", "lastName", "department", "workEmail", "status"]
    projection = fields if fields else default_fields
    projected = _project(filtered, projection)

    # ── Metadata ──────────────────────────────────────────────────────
    meta: dict[str, Any] = {
        "source": "ttl_cache",
        "cached_total": len(all_employees),
        "filters_applied": {
            "department": department,
            "birth_month": birth_month,
        },
        "fields_returned": projection,
    }
    if truncated:
        meta["warning"] = (
            f"Result truncated to {effective_limit} records (out of "
            f"{total_before_limit} matches). Please narrow your search "
            f"with more specific filters."
        )

    return {
        "results": projected,
        "count": len(projected),
        "total_before_limit": total_before_limit,
        "_meta": meta,
    }


# ---------------------------------------------------------------------------
# Tool 2: get_employee_statistics
# ---------------------------------------------------------------------------

@require_auth
def get_employee_statistics(
    metric: str,
    department: str | None = None,
) -> dict[str, Any]:
    """[READ] Compute employee statistics server-side. Returns only the final number, never raw rows.

    The LLM should use this tool instead of counting or averaging over large employee lists.

    Args:
        metric: One of 'headcount', 'average_age', 'department_distribution', 'tenure_distribution'.
        department: Optional department filter (case-insensitive substring).

    Returns:
        Computed result object (e.g. {"metric": "average_age", "value": 31.4, ...}).
    """
    all_employees = fetch_all_employees()

    # Optional department filter
    if department:
        dept_lower = department.lower()
        pool = [e for e in all_employees if dept_lower in (e.get("department") or "").lower()]
    else:
        pool = list(all_employees)

    if not pool:
        return {
            "metric": metric,
            "error": True,
            "message": "No employees match the given filters.",
            "department_filter": department,
        }

    today = date.today()

    if metric == "headcount":
        return {
            "metric": "headcount",
            "value": len(pool),
            "department_filter": department,
        }

    elif metric == "average_age":
        ages: list[float] = []
        for emp in pool:
            bd = emp.get("birthDate") or ""
            try:
                born = datetime.fromisoformat(bd[:10]).date()
                age = (today - born).days / 365.25
                ages.append(age)
            except (ValueError, TypeError):
                continue
        if not ages:
            return {
                "metric": "average_age",
                "error": True,
                "message": "No birth dates available to compute average age.",
            }
        avg = sum(ages) / len(ages)
        return {
            "metric": "average_age",
            "value": round(avg, 1),
            "sample_size": len(ages),
            "min_age": round(min(ages), 1),
            "max_age": round(max(ages), 1),
            "department_filter": department,
        }

    elif metric == "department_distribution":
        dist: dict[str, int] = {}
        for emp in pool:
            dept = emp.get("department") or "Unknown"
            dist[dept] = dist.get(dept, 0) + 1
        # Sort by count descending
        sorted_dist = dict(sorted(dist.items(), key=lambda x: x[1], reverse=True))
        return {
            "metric": "department_distribution",
            "total": len(pool),
            "departments": sorted_dist,
            "department_count": len(sorted_dist),
        }

    elif metric == "tenure_distribution":
        buckets = {"<1 year": 0, "1-3 years": 0, "3-5 years": 0, "5-10 years": 0, "10+ years": 0}
        for emp in pool:
            start = emp.get("employmentStartDate") or ""
            try:
                start_date = datetime.fromisoformat(start[:10]).date()
                years = (today - start_date).days / 365.25
            except (ValueError, TypeError):
                continue
            if years < 1:
                buckets["<1 year"] += 1
            elif years < 3:
                buckets["1-3 years"] += 1
            elif years < 5:
                buckets["3-5 years"] += 1
            elif years < 10:
                buckets["5-10 years"] += 1
            else:
                buckets["10+ years"] += 1
        return {
            "metric": "tenure_distribution",
            "total": len(pool),
            "buckets": buckets,
            "department_filter": department,
        }

    else:
        return {
            "metric": metric,
            "error": True,
            "message": (
                f"Unknown metric '{metric}'. "
                "Supported: headcount, average_age, department_distribution, tenure_distribution."
            ),
        }


# ---------------------------------------------------------------------------
# Tool 3: get_cache_status (no auth required — operational diagnostic)
# ---------------------------------------------------------------------------

def get_cache_status() -> dict[str, Any]:
    """[READ] Check the status of the employee data cache. No authentication required.

    Returns whether data is cached, entry count, age, TTL, and time until expiry.
    Use this to understand if data is fresh or stale before making queries.
    """
    return cache_status()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register(mcp: Any) -> None:
    """Register smart proxy tools with the FastMCP server."""
    mcp.add_tool(Tool.from_function(
        search_employees,
        annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read", "smart_proxy"},
    ))
    mcp.add_tool(Tool.from_function(
        get_employee_statistics,
        annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read", "smart_proxy", "analytics"},
    ))
    mcp.add_tool(Tool.from_function(
        get_cache_status,
        annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read", "smart_proxy", "diagnostic"},
    ))
