"""Chart-ready data aggregation for HR visualizations.

Pre-aggregates raw Kolay IK API data into payloads shaped for direct
Chart.js / ECharts consumption.  The LLM drops these into a template
instead of computing aggregations itself -- dramatically reducing
hallucination risk.

Functions:
  - leave_usage_by_department   -> pie/bar  (leave counts per unit)
  - headcount_by_department     -> bar/treemap  (employee counts per unit)
  - attendance_heatmap          -> ECharts calendar heatmap
  - headcount_trend             -> line  (joiners vs leavers over months)
  - leave_type_breakdown        -> doughnut/pie  (leave type distribution)
  - overtime_by_department      -> bar  (overtime hours per unit)

All functions return a consistent envelope:
  {
    "chart_type": "pie" | "bar" | "calendar_heatmap" | ...,
    "title": "...",
    "labels": [...],
    "datasets": [...],
    "reasoning_chain": [...]
  }
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from . import leave as leave_svc
from . import person as person_svc
from . import timelog as timelog_svc
from . import unit as unit_svc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> date:
    return datetime.fromisoformat(s[:10]).date()


def _flatten_units(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Depth-first flatten of the unit tree."""
    flat: list[dict[str, Any]] = []

    def _walk(node: dict[str, Any]) -> None:
        flat.append(node)
        for child in node.get("children") or []:
            _walk(child)

    for n in nodes:
        _walk(n)
    return flat


def _dept_name(person: dict[str, Any]) -> str:
    """Extract department name from a person record."""
    return (
        person.get("department")
        or (person.get("unit") or {}).get("name")
        or "Unassigned"
    )


def _full_name(person: dict[str, Any]) -> str:
    return f"{person.get('firstName', '')} {person.get('lastName', '')}".strip()


# ---------------------------------------------------------------------------
# Chart 1 -- Leave usage by department (pie / bar)
# ---------------------------------------------------------------------------

def leave_usage_by_department(
    *,
    start: str | None = None,
    end: str | None = None,
    status: str = "approved",
) -> dict[str, Any]:
    """Aggregate leave day-counts per department.

    Returns chart-ready payload for pie or bar visualization.
    """
    chain: list[str] = []

    year = str(datetime.now().year)
    s = start or f"{year}-01-01"
    e = end or f"{year}-12-31"

    chain.append(f"Step 1: Fetching {status} leaves from {s} to {e}.")
    leaves = leave_svc.list_leaves(status=status, start=s, end=e, limit=200)
    chain.append(f"Step 1 result: {len(leaves)} leave record(s) fetched.")

    chain.append("Step 2: Aggregating day counts by department.")
    dept_days: Counter[str] = Counter()
    for lv in leaves:
        person = lv.get("person") or {}
        dept = _dept_name(person)
        days = float(lv.get("dayCount") or lv.get("day_count") or 1)
        dept_days[dept] += days

    # Sort descending by days
    sorted_depts = dept_days.most_common()
    labels = [d[0] for d in sorted_depts]
    values = [d[1] for d in sorted_depts]
    chain.append(f"Step 2 result: {len(labels)} department(s) with leave data.")

    return {
        "chart_type": "pie",
        "chart_type_alternatives": ["bar", "doughnut"],
        "title": f"Leave Usage by Department ({s} to {e})",
        "labels": labels,
        "datasets": [{"label": "Leave Days", "data": values}],
        "total_days": sum(values),
        "total_records": len(leaves),
        "period": {"start": s, "end": e},
        "reasoning_chain": chain,
    }


# ---------------------------------------------------------------------------
# Chart 2 -- Headcount by department (bar / treemap)
# ---------------------------------------------------------------------------

def headcount_by_department() -> dict[str, Any]:
    """Count active employees per organisational unit.

    Returns chart-ready payload for bar or treemap visualization.
    """
    chain: list[str] = []

    chain.append("Step 1: Fetching unit tree for department structure.")
    tree = unit_svc.unit_tree()
    flat = _flatten_units(tree)
    chain.append(f"Step 1 result: {len(flat)} unit(s) found in tree.")

    chain.append("Step 2: Counting members per unit.")
    dept_counts: list[tuple[str, int]] = []
    total = 0
    for unit in flat:
        name = unit.get("name", "Unknown")
        items = unit.get("items") or []
        count = len(items)
        if count > 0:
            dept_counts.append((name, count))
            total += count

    # Sort descending
    dept_counts.sort(key=lambda x: x[1], reverse=True)
    labels = [d[0] for d in dept_counts]
    values = [d[1] for d in dept_counts]
    chain.append(f"Step 2 result: {len(labels)} unit(s) with members, {total} total.")

    return {
        "chart_type": "bar",
        "chart_type_alternatives": ["treemap", "pie", "doughnut"],
        "title": "Headcount by Department",
        "labels": labels,
        "datasets": [{"label": "Employees", "data": values}],
        "total_employees": total,
        "reasoning_chain": chain,
    }


# ---------------------------------------------------------------------------
# Chart 3 -- Attendance heatmap (ECharts calendar heatmap)
# ---------------------------------------------------------------------------

def attendance_heatmap(
    *,
    year: str | None = None,
) -> dict[str, Any]:
    """Build a calendar heatmap of daily absence counts for the year.

    Returns data shaped for ECharts calendarHeatmap:
      [[date_string, count], ...]
    """
    chain: list[str] = []
    yr = year or str(datetime.now().year)

    chain.append(f"Step 1: Fetching approved leaves for {yr}.")
    leaves = leave_svc.list_leaves(
        status="approved", start=f"{yr}-01-01", end=f"{yr}-12-31", limit=200,
    )
    chain.append(f"Step 1 result: {len(leaves)} leave record(s).")

    chain.append("Step 2: Building daily absence count map.")
    day_counts: Counter[str] = Counter()
    for lv in leaves:
        try:
            sd = _parse_date(str(lv.get("startDate", "")))
            ed = _parse_date(str(lv.get("endDate", "")))
        except (ValueError, TypeError):
            continue
        cursor = sd
        while cursor <= ed:
            day_counts[cursor.isoformat()] += 1
            cursor += timedelta(days=1)

    # Convert to sorted list of [date, count]
    heatmap_data = sorted(
        [[d, c] for d, c in day_counts.items()],
        key=lambda x: x[0],
    )

    peak_day = max(day_counts, key=day_counts.get, default=None) if day_counts else None  # type: ignore[arg-type]
    peak_count = day_counts[peak_day] if peak_day else 0

    chain.append(
        f"Step 2 result: {len(heatmap_data)} day(s) with absences. "
        f"Peak: {peak_count} on {peak_day or 'N/A'}."
    )

    return {
        "chart_type": "calendar_heatmap",
        "library": "echarts",
        "title": f"Absence Heatmap ({yr})",
        "year": yr,
        "data": heatmap_data,
        "max_value": peak_count,
        "peak_day": peak_day,
        "total_absence_days": sum(day_counts.values()),
        "reasoning_chain": chain,
    }


# ---------------------------------------------------------------------------
# Chart 4 -- Headcount trend (line: joiners vs leavers)
# ---------------------------------------------------------------------------

def headcount_trend(
    *,
    months: int = 12,
) -> dict[str, Any]:
    """Monthly joiners and leavers for a line chart trend.

    Fetches active + terminated employees and buckets by employment start /
    termination month.
    """
    chain: list[str] = []

    chain.append(f"Step 1: Fetching active employees (limit 200).")
    active_result = person_svc.list_people(status="active", limit=200)
    active = active_result.get("items", [])
    chain.append(f"Step 1a: {len(active)} active employee(s) fetched.")

    chain.append("Step 1b: Fetching terminated employees.")
    termed_result = person_svc.list_people(status="passive", limit=200)
    termed = termed_result.get("items", [])
    chain.append(f"Step 1b result: {len(termed)} terminated employee(s).")

    chain.append(f"Step 2: Bucketing into {months} monthly bins.")
    today = date.today()
    cutoff = today - timedelta(days=months * 30)

    # Build month labels
    month_labels: list[str] = []
    cursor = date(cutoff.year, cutoff.month, 1)
    while cursor <= today:
        month_labels.append(cursor.strftime("%Y-%m"))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    joiners: Counter[str] = Counter()
    leavers: Counter[str] = Counter()

    for p in active + termed:
        start_str = p.get("employmentStartDate") or p.get("employmentStart") or ""
        if start_str:
            try:
                start_month = _parse_date(start_str).strftime("%Y-%m")
                if start_month in month_labels:
                    joiners[start_month] += 1
            except (ValueError, TypeError):
                pass

    for p in termed:
        term_str = p.get("terminationDate") or p.get("employmentEndDate") or ""
        if term_str:
            try:
                term_month = _parse_date(term_str).strftime("%Y-%m")
                if term_month in month_labels:
                    leavers[term_month] += 1
            except (ValueError, TypeError):
                pass

    joined_data = [joiners.get(m, 0) for m in month_labels]
    left_data = [leavers.get(m, 0) for m in month_labels]

    # Human-readable month labels
    display_labels = []
    for m in month_labels:
        d = datetime.strptime(m, "%Y-%m")
        display_labels.append(d.strftime("%b %Y"))

    chain.append(
        f"Step 2 result: {sum(joined_data)} joiner(s), {sum(left_data)} leaver(s) "
        f"across {len(month_labels)} month(s)."
    )

    return {
        "chart_type": "line",
        "chart_type_alternatives": ["bar"],
        "title": f"Headcount Trend (Last {months} Months)",
        "labels": display_labels,
        "datasets": [
            {"label": "Joined", "data": joined_data},
            {"label": "Left", "data": left_data},
        ],
        "period_months": months,
        "total_joined": sum(joined_data),
        "total_left": sum(left_data),
        "net_change": sum(joined_data) - sum(left_data),
        "reasoning_chain": chain,
    }


# ---------------------------------------------------------------------------
# Chart 5 -- Leave type breakdown (doughnut / pie)
# ---------------------------------------------------------------------------

def leave_type_breakdown(
    *,
    start: str | None = None,
    end: str | None = None,
    status: str = "approved",
) -> dict[str, Any]:
    """Aggregate leave counts by leave type.

    Returns chart-ready payload for doughnut or pie chart.
    """
    chain: list[str] = []

    year = str(datetime.now().year)
    s = start or f"{year}-01-01"
    e = end or f"{year}-12-31"

    chain.append(f"Step 1: Fetching {status} leaves from {s} to {e}.")
    leaves = leave_svc.list_leaves(status=status, start=s, end=e, limit=200)
    chain.append(f"Step 1 result: {len(leaves)} leave record(s).")

    chain.append("Step 2: Grouping by leave type.")
    type_days: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    for lv in leaves:
        lt = (lv.get("leaveType") or {}).get("name") or "Other"
        days = float(lv.get("dayCount") or lv.get("day_count") or 1)
        type_days[lt] += days
        type_counts[lt] += 1

    sorted_types = type_days.most_common()
    labels = [t[0] for t in sorted_types]
    values = [t[1] for t in sorted_types]
    counts = [type_counts[t[0]] for t in sorted_types]

    chain.append(f"Step 2 result: {len(labels)} leave type(s).")

    return {
        "chart_type": "doughnut",
        "chart_type_alternatives": ["pie", "bar"],
        "title": f"Leave Type Breakdown ({s} to {e})",
        "labels": labels,
        "datasets": [
            {"label": "Days", "data": values},
        ],
        "request_counts": counts,
        "total_days": sum(values),
        "total_requests": sum(counts),
        "period": {"start": s, "end": e},
        "reasoning_chain": chain,
    }


# ---------------------------------------------------------------------------
# Chart 6 -- Overtime by department (bar)
# ---------------------------------------------------------------------------

def overtime_by_department(
    *,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any]:
    """Aggregate overtime hours per department from timelogs.

    Returns chart-ready payload for bar chart.
    """
    chain: list[str] = []

    year = str(datetime.now().year)
    s = start or f"{year}-01-01"
    e = end or f"{year}-12-31"

    chain.append(f"Step 1: Fetching overtime timelogs from {s} to {e}.")
    result = timelog_svc.list_timelogs(
        start=s, end=e, type="overtime", limit=200,
    )
    timelogs = result.get("items", [])
    chain.append(f"Step 1 result: {len(timelogs)} overtime record(s).")

    chain.append("Step 2: Aggregating hours by department.")
    dept_hours: Counter[str] = Counter()
    for tl in timelogs:
        person = tl.get("person") or {}
        dept = _dept_name(person)
        # Calculate hours from startDate / endDate
        try:
            start_dt = datetime.fromisoformat(str(tl.get("startDate", "")))
            end_dt = datetime.fromisoformat(str(tl.get("endDate", "")))
            hours = (end_dt - start_dt).total_seconds() / 3600
        except (ValueError, TypeError):
            hours = float(tl.get("hours") or tl.get("duration") or 0)
        dept_hours[dept] += round(hours, 1)

    sorted_depts = dept_hours.most_common()
    labels = [d[0] for d in sorted_depts]
    values = [d[1] for d in sorted_depts]

    chain.append(f"Step 2 result: {len(labels)} department(s), {sum(values):.1f} total hours.")

    return {
        "chart_type": "bar",
        "chart_type_alternatives": ["line"],
        "title": f"Overtime Hours by Department ({s} to {e})",
        "labels": labels,
        "datasets": [{"label": "Overtime Hours", "data": values}],
        "total_hours": round(sum(values), 1),
        "total_records": len(timelogs),
        "period": {"start": s, "end": e},
        "reasoning_chain": chain,
    }
