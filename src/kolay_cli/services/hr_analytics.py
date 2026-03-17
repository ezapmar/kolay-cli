"""HR analytics and intelligence services.

Multi-step reasoning functions that cross-reference multiple Kolay IK
APIs to produce structured, LLM-agnostic JSON insights:

  - team_availability_analysis  → Leave API × Unit API → operational risk
  - turnover_risk_scan          → Person API × Leave balance → risk ranking
  - payroll_anomaly_detect      → Transaction API → duplicate / outlier flags

Each public function documents its reasoning steps in a 'reasoning_chain'
key so the full decision trail is auditable by humans and any downstream LLM.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from . import leave as leave_svc
from . import person as person_svc
from . import transaction as transaction_svc
from . import unit as unit_svc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> date:
    return datetime.fromisoformat(s[:10]).date()


def _tenure_months(employment_start: str) -> float:
    try:
        delta = date.today() - _parse_date(employment_start)
        return delta.days / 30.44
    except (ValueError, TypeError):
        return 0.0


def _risk_label(score: int) -> str:
    if score >= 4:
        return "critical"
    if score >= 3:
        return "high"
    if score >= 2:
        return "medium"
    if score >= 1:
        return "low"
    return "normal"


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


# ---------------------------------------------------------------------------
# Tool 1 — Team availability & operational risk
# ---------------------------------------------------------------------------

def team_availability_analysis(
    unit_name: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """
    Multi-step team availability and operational risk assessment.

    Reasoning plan:
      Step 1 — Resolve unit_name → member person IDs via unit_tree().
      Step 2 — Fetch approved leaves in [start_date, end_date] for those members.
      Step 3 — Iterate every calendar day to find peak concurrent absences.
      Step 4 — Classify operational risk (normal / low / medium / high / critical).
    """
    chain: list[str] = []

    # ── Step 1: resolve unit ──────────────────────────────────────────────
    chain.append(f"Step 1: Calling unit_tree() to locate unit matching '{unit_name}'.")
    flat = _flatten_units(unit_svc.unit_tree())
    matched = next(
        (n for n in flat if unit_name.lower() in n.get("name", "").lower()),
        None,
    )
    if matched is None:
        return {
            "error": True,
            "message": f"Unit '{unit_name}' not found in org chart.",
            "available_units": [n.get("name", "") for n in flat],
            "reasoning_chain": chain,
        }

    member_ids: set[str] = {
        str(item.get("personId") or item.get("id", ""))
        for item in (matched.get("items") or [])
        if item.get("personId") or item.get("id")
    }
    headcount = len(member_ids)
    chain.append(
        f"Step 1 result: Matched unit '{matched['name']}' — {headcount} member(s) found."
    )

    if headcount == 0:
        return {
            "error": True,
            "message": f"Unit '{unit_name}' has no member records.",
            "reasoning_chain": chain,
        }

    # ── Step 2: fetch leaves ──────────────────────────────────────────────
    chain.append(
        f"Step 2: Calling leave_list(status='approved', start='{start_date}', "
        f"end='{end_date}', limit=200) and filtering to unit members."
    )
    all_leaves = leave_svc.list_leaves(
        status="approved", start=start_date, end=end_date, limit=200
    )
    unit_leaves = [
        lv for lv in all_leaves
        if str((lv.get("person") or {}).get("id", "")) in member_ids
    ]
    chain.append(
        f"Step 2 result: {len(unit_leaves)} approved leave record(s) affect this unit in the period."
    )

    # ── Step 3: daily absence map ─────────────────────────────────────────
    chain.append("Step 3: Building daily absence map across the full date range.")
    start_d, end_d = _parse_date(start_date), _parse_date(end_date)
    days_total = (end_d - start_d).days + 1
    absence_by_day: dict[str, list[str]] = {}

    cursor = start_d
    while cursor <= end_d:
        day_str = cursor.isoformat()
        names_out: list[str] = []
        for lv in unit_leaves:
            try:
                if _parse_date(lv["startDate"]) <= cursor <= _parse_date(lv["endDate"]):
                    p = lv.get("person") or {}
                    names_out.append(p.get("name") or str(p.get("id", "?")))
            except (KeyError, ValueError):
                continue
        absence_by_day[day_str] = names_out
        cursor += timedelta(days=1)

    peak_day = max(absence_by_day, key=lambda d: len(absence_by_day[d]))
    peak_count = len(absence_by_day[peak_day])
    avg_absent = sum(len(v) for v in absence_by_day.values()) / max(days_total, 1)
    availability_pct = round(100.0 * (1.0 - avg_absent / headcount), 1)

    chain.append(
        f"Step 3 result: Peak absence {peak_count}/{headcount} on {peak_day}. "
        f"Average daily absence {avg_absent:.1f}. Availability {availability_pct}%."
    )

    # ── Step 4: classify risk ─────────────────────────────────────────────
    chain.append("Step 4: Classifying operational risk from absence ratio and team size.")
    ratio = peak_count / headcount
    risk_factors: list[str] = []
    score = 0

    for threshold, pts, label in [
        (0.50, 4, f"≥50 % of team absent simultaneously on {peak_day}"),
        (0.35, 3, f"≥35 % of team absent simultaneously on {peak_day}"),
        (0.25, 2, f"≥25 % of team absent simultaneously on {peak_day}"),
        (0.15, 1, f"≥15 % of team absent simultaneously on {peak_day}"),
    ]:
        if ratio >= threshold:
            score = pts
            risk_factors.append(label)
            break

    if headcount < 4:
        score += 1
        risk_factors.append("Small team (< 4 members) — every absence is high-impact")

    risk = _risk_label(score)
    chain.append(
        f"Step 4 result: Operational risk = '{risk}' (score={score}). "
        f"Factors: {risk_factors or ['none']}."
    )

    members_on_leave = [
        {
            "name": (lv.get("person") or {}).get("name", ""),
            "leave_type": (lv.get("leaveType") or {}).get("name", ""),
            "start": str(lv.get("startDate", ""))[:10],
            "end": str(lv.get("endDate", ""))[:10],
            "days": lv.get("dayCount"),
        }
        for lv in unit_leaves
    ]

    return {
        "unit": matched["name"],
        "period": {"start": start_date, "end": end_date},
        "headcount_total": headcount,
        "leaves_in_period": len(unit_leaves),
        "peak_absence_day": peak_day,
        "peak_absence_count": peak_count,
        "availability_pct": availability_pct,
        "operational_risk": risk,
        "risk_score": score,
        "risk_factors": risk_factors,
        "members_on_leave": members_on_leave,
        "reasoning_chain": chain,
    }


# ---------------------------------------------------------------------------
# Tool 2 — Turnover / burnout risk scan
# ---------------------------------------------------------------------------

# Signal catalogue: key → (human label, risk points)
_SIGNALS: dict[str, tuple[str, int]] = {
    "unused_critical": ("Unused annual leave > 30 days — severe burnout indicator", 3),
    "unused_high":     ("Unused annual leave > 20 days — burnout risk", 2),
    "unused_moderate": ("Unused annual leave > 15 days — monitor", 1),
    "new_hire":        ("Tenure < 6 months — early flight-risk window", 1),
    "zero_leave_long": ("Tenure > 24 months, 0 days leave taken — disengagement signal", 2),
    "zero_leave_new":  ("No annual leave taken yet", 1),
}


def _score_person(
    person: dict[str, Any],
    balances: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score a single employee. Pure function — no API calls."""
    signals: list[str] = []
    score = 0

    start_str = person.get("employmentStartDate") or person.get("employmentStart") or ""
    tenure = _tenure_months(start_str) if start_str else 0.0

    if 0 < tenure < 6:
        label, pts = _SIGNALS["new_hire"]
        signals.append(label)
        score += pts

    # Find the primary (annual) leave balance
    annual = next(
        (b for b in balances
         if b.get("primary") or "annual" in (b.get("leaveType") or {}).get("name", "").lower()),
        None,
    )
    if annual:
        unused = float(annual.get("unused") or 0)
        entitled = float(annual.get("entitled") or 0)
        used = entitled - unused

        if unused > 30:
            label, pts = _SIGNALS["unused_critical"]
            signals.append(label)
            score += pts
        elif unused > 20:
            label, pts = _SIGNALS["unused_high"]
            signals.append(label)
            score += pts
        elif unused > 15:
            label, pts = _SIGNALS["unused_moderate"]
            signals.append(label)
            score += pts

        if entitled > 0 and used <= 0:
            key = "zero_leave_long" if tenure > 24 else "zero_leave_new"
            label, pts = _SIGNALS[key]
            signals.append(label)
            score += pts

    name = f"{person.get('firstName', '')} {person.get('lastName', '')}".strip()
    dept = person.get("department") or (person.get("unit") or {}).get("name") or ""

    return {
        "person_id": person.get("id", ""),
        "name": name,
        "department": dept,
        "tenure_months": round(tenure, 1),
        "risk_score": score,
        "risk_level": _risk_label(score),
        "signals": signals,
    }


def turnover_risk_scan(
    search: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Scan active employees for turnover and burnout risk signals.

    Reasoning plan:
      Step 1 — Fetch active employees (optionally filtered by search/department name).
      Step 2 — Fetch leave balances per employee via person_leave_status().
      Step 3 — Apply risk signal heuristics and rank by score (highest first).
    """
    chain: list[str] = []

    # ── Step 1 ────────────────────────────────────────────────────────────
    chain.append(
        f"Step 1: Calling person_list(status='active', limit={limit}"
        + (f", search='{search}')" if search else ").")
    )
    result = person_svc.list_people(status="active", search=search, limit=limit)
    people = result.get("items", [])
    total_active = result.get("totalCount", len(people))
    chain.append(
        f"Step 1 result: {len(people)} employees fetched (total active in org: {total_active})."
    )

    if not people:
        return {
            "error": True,
            "message": "No active employees found.",
            "reasoning_chain": chain,
        }

    # ── Step 2 ────────────────────────────────────────────────────────────
    chain.append(
        f"Step 2: Fetching annual leave balances for each of the "
        f"{len(people)} employees via person_leave_status()."
    )
    scored: list[dict[str, Any]] = []
    errors = 0
    for person in people:
        try:
            balances = person_svc.leave_status(person["id"])
        except Exception:
            balances = []
            errors += 1
        scored.append(_score_person(person, balances))

    chain.append(
        f"Step 2 result: Balances fetched for {len(scored) - errors}/{len(scored)} employees "
        f"({errors} fetch error(s) — those employees scored with zero leave data)."
    )

    # ── Step 3 ────────────────────────────────────────────────────────────
    chain.append("Step 3: Ranking employees by risk_score descending and summarising distribution.")
    scored.sort(key=lambda e: e["risk_score"], reverse=True)

    dist: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "normal": 0}
    for e in scored:
        dist[e["risk_level"]] += 1

    at_risk = [e for e in scored if e["risk_score"] > 0]
    chain.append(
        f"Step 3 result: {len(at_risk)}/{len(scored)} employees have at least one risk signal. "
        f"Risk distribution: {dist}."
    )

    return {
        "scanned": len(scored),
        "total_active_employees": total_active,
        "at_risk_count": len(at_risk),
        "risk_distribution": dist,
        "employees": scored,
        "reasoning_chain": chain,
    }


# ---------------------------------------------------------------------------
# Tool 3 — Payroll anomaly detection
# ---------------------------------------------------------------------------

def payroll_anomaly_detect(months_back: int = 3) -> dict[str, Any]:
    """
    Scan recent transactions for payroll anomalies.

    Reasoning plan:
      Step 1 — Fetch transactions for the last `months_back` months.
      Step 2 — Flag same-person / same-type / same-date duplicates.
      Step 3 — Compute per-type mean + stdev; flag amounts > mean + 2σ.
    """
    chain: list[str] = []

    # ── Step 1 ────────────────────────────────────────────────────────────
    cutoff = (date.today() - timedelta(days=months_back * 30)).isoformat()
    chain.append(
        f"Step 1: Calling transaction_list(limit=200) and filtering to transactions "
        f"on or after {cutoff} (last {months_back} month(s))."
    )
    result = transaction_svc.list_transactions(limit=200)
    txns = [
        t for t in result.get("items", [])
        if str(t.get("date") or "")[:10] >= cutoff
    ]
    chain.append(f"Step 1 result: {len(txns)} transaction(s) in scope.")

    if not txns:
        return {
            "period_start": cutoff,
            "transactions_scanned": 0,
            "anomalies_found": 0,
            "anomalies": [],
            "summary": {"duplicates": 0, "statistical_outliers": 0},
            "reasoning_chain": chain,
        }

    # ── Step 2: duplicate detection ───────────────────────────────────────
    chain.append(
        "Step 2: Grouping by (person_id, type, date) to detect same-day duplicate transactions."
    )
    key_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for t in txns:
        p = t.get("person") or {}
        key = (str(p.get("id", "")), str(t.get("type", "")), str(t.get("date", ""))[:10])
        key_groups[key].append(t)

    anomalies: list[dict[str, Any]] = []
    for (pid, txn_type, txn_date), group in key_groups.items():
        if len(group) > 1:
            p0 = group[0].get("person") or {}
            person_name = f"{p0.get('firstName', '')} {p0.get('lastName', '')}".strip()
            anomalies.append({
                "anomaly_type": "duplicate_transaction",
                "severity": "high",
                "description": (
                    f"{len(group)} '{txn_type}' entries for {person_name} on {txn_date}"
                ),
                "person_id": pid,
                "person_name": person_name,
                "transaction_ids": [t.get("id", "") for t in group],
                "total_amount": round(sum(float(t.get("amount") or 0) for t in group), 2),
            })

    dup_count = len(anomalies)
    chain.append(f"Step 2 result: {dup_count} duplicate group(s) flagged.")

    # ── Step 3: statistical outliers ─────────────────────────────────────
    chain.append(
        "Step 3: Computing per-type amount statistics; flagging transactions > mean + 2σ."
    )
    by_type: dict[str, list[float]] = defaultdict(list)
    for t in txns:
        amt = float(t.get("amount") or 0)
        if amt > 0:
            by_type[str(t.get("type", "unknown"))].append(amt)

    outlier_count = 0
    for txn_type, amounts in by_type.items():
        if len(amounts) < 4:
            continue  # insufficient data for reliable statistics
        mean = statistics.mean(amounts)
        stdev = statistics.stdev(amounts)
        threshold = mean + 2 * stdev
        for t in txns:
            if str(t.get("type", "")) != txn_type:
                continue
            amt = float(t.get("amount") or 0)
            if amt > threshold:
                p = t.get("person") or {}
                person_name = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip()
                anomalies.append({
                    "anomaly_type": "statistical_outlier",
                    "severity": "medium",
                    "description": (
                        f"{txn_type} of {amt:,.2f} for {person_name} exceeds 2σ threshold "
                        f"({threshold:,.2f}; mean={mean:,.2f}, σ={stdev:,.2f})"
                    ),
                    "person_id": str(p.get("id", "")),
                    "person_name": person_name,
                    "transaction_id": t.get("id", ""),
                    "amount": amt,
                    "type_mean": round(mean, 2),
                    "type_stdev": round(stdev, 2),
                    "threshold": round(threshold, 2),
                })
                outlier_count += 1

    chain.append(f"Step 3 result: {outlier_count} statistical outlier(s) flagged.")

    # Sort high severity first
    severity_order = {"high": 0, "medium": 1, "low": 2}
    anomalies.sort(key=lambda a: severity_order.get(str(a.get("severity")), 2))

    return {
        "period_start": cutoff,
        "transactions_scanned": len(txns),
        "anomalies_found": len(anomalies),
        "anomalies": anomalies,
        "summary": {"duplicates": dup_count, "statistical_outliers": outlier_count},
        "reasoning_chain": chain,
    }
