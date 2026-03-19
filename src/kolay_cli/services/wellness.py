"""Wellbeing and smart rest planning engine.

Provides:
  - analyze_employee_wellbeing()  →  per-employee burnout + bridge-day report
  - get_smart_rest_plan()         →  ranked upcoming rest opportunities

Follows the same reasoning_chain pattern as hr_analytics.py.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from . import leave as leave_svc
from . import person as person_svc
from .turkish_holidays import get_holidays, is_off_day

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
_REST_GAP_RED    = 90   # 90+ days without rest = red zone
_REST_GAP_ORANGE = 60
_REST_GAP_YELLOW = 30

_BALANCE_CONSERVATIVE = 5   # <5 days: suggest long weekends only
_BALANCE_GENEROUS     = 15  # >=15 days: suggest full weeks too

_BRIDGE_HORIZON = 90   # days ahead to scan for bridge opportunities
_PLAN_HORIZON   = 90   # days ahead for smart rest plan


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _days_since_last_rest(leave_history: list[dict[str, Any]]) -> int | None:
    """Return days since the most recent approved leave ended. None if no history."""
    last_end: date | None = None
    for lv in leave_history:
        raw = str(lv.get("endDate") or "")[:10]
        if not raw:
            continue
        try:
            d = date.fromisoformat(raw)
            if last_end is None or d > last_end:
                last_end = d
        except ValueError:
            continue
    if last_end is None:
        return None
    return (date.today() - last_end).days


def _burnout_status(score: int) -> str:
    if score >= 4:
        return "red_zone"
    if score >= 3:
        return "orange_zone"
    if score >= 2:
        return "yellow_zone"
    return "healthy"


def _burnout_emoji(status: str) -> str:
    return {"red_zone": "🔴", "orange_zone": "🟠", "yellow_zone": "🟡", "healthy": "🟢"}.get(status, "⚪")


def _gap_signal(days: int | None) -> tuple[str, int]:
    """Return (signal_text, score_points) for leave gap."""
    if days is None:
        return ("No approved leave on record", 1)
    if days >= _REST_GAP_RED:
        return (f"No rest taken in {days} days (90-day threshold exceeded)", 3)
    if days >= _REST_GAP_ORANGE:
        return (f"Last rest was {days} days ago (moderate risk)", 2)
    if days >= _REST_GAP_YELLOW:
        return (f"Last rest was {days} days ago (monitor)", 1)
    return ("", 0)


def _scan_bridge_opportunities(
    holidays: dict[date, str],
    balance_days: float,
) -> list[dict[str, Any]]:
    """Find bridge day opportunities in the next _BRIDGE_HORIZON days.

    A bridge opportunity is any window where:
      - There is at least one holiday/weekend cluster
      - Taking 1-5 extra working days extends the break significantly
    Returns a list of opportunities sorted by efficiency desc.
    """
    today = date.today()
    end = today + timedelta(days=_BRIDGE_HORIZON)

    # Build a set of all "off days" (we will scan working-day windows around them)
    all_off: set[date] = set()
    cursor = today
    while cursor <= end:
        if is_off_day(cursor, holidays):
            all_off.add(cursor)
        cursor += timedelta(days=1)

    opportunities: list[dict[str, Any]] = []
    seen: set[date] = set()

    for holiday_date, holiday_name in holidays.items():
        if holiday_date < today or holiday_date > end:
            continue
        if holiday_date in seen:
            continue

        # Expand the contiguous "off block" around this holiday
        block_start = block_end = holiday_date
        d = holiday_date - timedelta(days=1)
        while d >= today and is_off_day(d, holidays):
            block_start = d
            d -= timedelta(days=1)
        d = holiday_date + timedelta(days=1)
        while d <= end and is_off_day(d, holidays):
            block_end = d
            d += timedelta(days=1)

        # Mark all days in this block as seen so we don't duplicate
        c = block_start
        while c <= block_end:
            seen.add(c)
            c += timedelta(days=1)

        # Try bridging: 1-3 working days before and/or after the block
        for before in range(0, 4):
            for after in range(0, 4):
                if before + after == 0:
                    continue
                total_leave = before + after
                if total_leave > balance_days:
                    continue  # can't afford this bridge

                bridge_start = block_start - timedelta(days=before)
                bridge_end = block_end + timedelta(days=after)
                total_rest = (bridge_end - bridge_start).days + 1
                efficiency = round(total_rest / total_leave, 2) if total_leave else 0

                if efficiency < 2.0:
                    continue  # not worth it

                opportunities.append({
                    "leave_start": bridge_start.isoformat(),
                    "leave_end": bridge_end.isoformat(),
                    "adjacent_holiday": holiday_name,
                    "holiday_date": holiday_date.isoformat(),
                    "leave_days_cost": total_leave,
                    "total_rest_days": total_rest,
                    "efficiency": efficiency,
                    "description": (
                        f"Take {before + after} day(s) off around {holiday_name} "
                        f"({holiday_date.isoformat()}) → {total_rest}-day break"
                    ),
                })

    opportunities.sort(key=lambda o: o["efficiency"], reverse=True)
    return opportunities[:5]  # top 5 only


def _scan_rest_opportunities(
    holidays: dict[date, str],
    balance_days: float,
) -> list[dict[str, Any]]:
    """Return ranked rest windows based on budget tier."""
    today = date.today()
    end = today + timedelta(days=_PLAN_HORIZON)

    budget_tier: str
    if balance_days < _BALANCE_CONSERVATIVE:
        budget_tier = "conservative"
        max_consecutive_leave = 2
    elif balance_days < _BALANCE_GENEROUS:
        budget_tier = "balanced"
        max_consecutive_leave = 3
    else:
        budget_tier = "generous"
        max_consecutive_leave = 5

    opportunities: list[dict[str, Any]] = []
    seen_starts: set[date] = set()

    # Scan every possible leave start date
    cursor = today + timedelta(days=1)
    while cursor <= end - timedelta(days=1):
        if cursor.weekday() >= 5 or is_off_day(cursor, holidays):
            cursor += timedelta(days=1)
            continue
        if cursor in seen_starts:
            cursor += timedelta(days=1)
            continue

        for leave_len in range(1, max_consecutive_leave + 1):
            leave_end = cursor + timedelta(days=leave_len - 1)
            # Skip if bridge goes through more weekends than it's worth
            if leave_len > balance_days:
                continue

            # Expand backwards (free weekend before?)
            extended_start = cursor
            d = cursor - timedelta(days=1)
            while d >= today and is_off_day(d, holidays):
                extended_start = d
                d -= timedelta(days=1)

            # Expand forwards (free weekend/holiday after?)
            extended_end = leave_end
            d = leave_end + timedelta(days=1)
            while d <= end and is_off_day(d, holidays):
                extended_end = d
                d += timedelta(days=1)

            total_rest = (extended_end - extended_start).days + 1
            efficiency = round(total_rest / leave_len, 2)

            if efficiency < 1.5:
                continue

            seen_starts.add(cursor)
            opportunities.append({
                "take_leave_from": cursor.isoformat(),
                "take_leave_to": leave_end.isoformat(),
                "rest_from": extended_start.isoformat(),
                "rest_to": extended_end.isoformat(),
                "leave_days_cost": leave_len,
                "total_rest_days": total_rest,
                "efficiency": efficiency,
                "budget_tier": budget_tier,
            })

        cursor += timedelta(days=1)

    opportunities.sort(key=lambda o: o["efficiency"], reverse=True)
    return opportunities[:3]


# ---------------------------------------------------------------------------
# Public API: analyze_employee_wellbeing
# ---------------------------------------------------------------------------

def analyze_employee_wellbeing(person_id: str) -> dict[str, Any]:
    """Deep per-employee wellbeing assessment.

    Reasoning steps:
      1. Fetch person profile + leave balances.
      2. Fetch leave history (last 6 months) to assess rest recency.
      3. Score burnout signals (balance + recency + tenure).
      4. Scan upcoming Turkish public holidays for bridge opportunities.
      5. Generate status, signals, and recommendation.
    """
    chain: list[str] = []
    today = date.today()
    six_months_ago = (today - timedelta(days=182)).isoformat()

    # Step 1 — profile + balances
    chain.append("Step 1: Fetching employee profile and leave balances.")
    try:
        profile = person_svc.view_person(person_id)
    except Exception as exc:
        return {"error": True, "message": f"Person not found: {exc}", "reasoning_chain": chain}
    try:
        balances = person_svc.leave_status(person_id)
    except Exception as exc:
        _log.debug("[wellness-engine] Could not fetch balances for %s: %s", person_id, exc)
        balances = []

    name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
    dept = profile.get("department", "") or ""
    start_str = profile.get("employmentStartDate") or profile.get("employmentStart") or ""
    tenure_days = ((today - date.fromisoformat(start_str[:10])).days
                   if start_str else 0)

    # Find annual leave balance
    annual = next(
        (b for b in balances
         if b.get("primary") or "annual" in (b.get("leaveType") or {}).get("name", "").lower()),
        None,
    )
    unused_days: float = float(annual.get("unused") or 0) if annual else 0.0
    chain.append(
        f"Step 1 result: {name} — {dept}, tenure {tenure_days} days, "
        f"{unused_days:.0f} unused annual leave days."
    )

    # Step 2 — leave history
    chain.append(f"Step 2: Fetching approved leave history since {six_months_ago}.")
    try:
        history = leave_svc.list_leaves(
            status="approved", person_id=person_id,
            start=six_months_ago, limit=50,
        )
    except Exception as exc:
        _log.debug("[wellness-engine] Could not fetch history for %s: %s", person_id, exc)
        history = []

    days_since_rest = _days_since_last_rest(history)
    chain.append(
        f"Step 2 result: Found {len(history)} leave record(s). "
        f"Days since last rest: {days_since_rest if days_since_rest is not None else 'unknown'}."
    )

    # Step 3 — score burnout signals
    chain.append("Step 3: Computing burnout score from balance and recency signals.")
    signals: list[str] = []
    score = 0

    # Balance signals
    if unused_days > 30:
        signals.append("Unused annual leave > 30 days — severe burnout indicator")
        score += 3
    elif unused_days > 20:
        signals.append("Unused annual leave > 20 days — burnout risk")
        score += 2
    elif unused_days > 15:
        signals.append("Unused annual leave > 15 days — monitor")
        score += 1

    if annual and float(annual.get("entitled") or 0) > 0:
        used_days = float(annual.get("used") or 0)
        if used_days <= 0:
            if tenure_days > 720:
                signals.append("Tenure > 24 months with zero leave taken — disengagement signal")
                score += 2
            else:
                signals.append("No annual leave taken yet")
                score += 1

    # Recency signal
    gap_signal, gap_pts = _gap_signal(days_since_rest)
    if gap_pts > 0:
        signals.append(gap_signal)
        score += gap_pts

    # New hire risk
    if 0 < tenure_days < 180:
        signals.append("Tenure < 6 months — early flight-risk window")
        score += 1

    burnout_status = _burnout_status(score)
    chain.append(
        f"Step 3 result: Score={score}, status='{burnout_status}'. "
        f"Signals: {signals or ['none']}."
    )

    # Step 4 — holidays + bridge opportunities
    chain.append(
        f"Step 4: Scanning next {_BRIDGE_HORIZON} days for Turkish public holidays "
        "and bridge opportunities."
    )
    horizon_end = today + timedelta(days=_BRIDGE_HORIZON)
    holidays = get_holidays(today, horizon_end)
    bridges = _scan_bridge_opportunities(holidays, unused_days)
    chain.append(
        f"Step 4 result: {len(holidays)} holidays found in window, "
        f"{len(bridges)} bridge opportunities identified."
    )

    # Step 5 — recommendation
    chain.append("Step 5: Generating recommendation.")
    if bridges and score >= 2:
        best = bridges[0]
        rec = (
            f"{name} is in the {burnout_status.replace('_', ' ').title()}. "
            f"Recommendation: {best['description']} using only {best['leave_days_cost']} "
            f"leave credit(s) for a {best['total_rest_days']}-day break."
        )
    elif score == 0:
        rec = f"{name} shows no burnout signals. Stay consistent and book regular breaks."
    else:
        rec = (
            f"{name} shows moderate stress signals. "
            "Encourage them to use upcoming long weekends for short breaks."
        )

    # Tenant debug log
    _log.debug(
        "[wellness-engine] Calculating rest efficiency for person_id: %s", person_id
    )

    return {
        "employee": {"id": person_id, "name": name, "department": dept},
        "burnout_status": burnout_status,
        "burnout_emoji": _burnout_emoji(burnout_status),
        "burnout_score": score,
        "signals": signals,
        "days_since_last_rest": days_since_rest,
        "leave_balance": {
            "annual_unused": unused_days,
            "leave_type": (annual or {}).get("leaveType", {}).get("name", "Annual Leave") if annual else "N/A",
        },
        "bridge_day_opportunities": bridges,
        "upcoming_holidays": [
            {"date": d.isoformat(), "name": n}
            for d, n in sorted(holidays.items())[:8]
        ],
        "recommendation": rec,
        "reasoning_chain": chain,
    }


# ---------------------------------------------------------------------------
# Public API: get_smart_rest_plan
# ---------------------------------------------------------------------------

def get_smart_rest_plan(
    person_id: str,
    horizon_days: int = 90,
) -> dict[str, Any]:
    """Generate the top-3 upcoming rest opportunities ranked by leave efficiency.

    Budget tiers:
      <5 days  → conservative (long weekends only)
      5-15     → balanced (bridge days too)
      15+      → generous (full weeks considered)
    """
    _log.debug(
        "[wellness-engine] Calculating rest efficiency for person_id: %s", person_id
    )
    chain: list[str] = []
    today = date.today()

    # Fetch balance
    chain.append("Step 1: Fetching leave balance to determine budget tier.")
    try:
        balances = person_svc.leave_status(person_id)
    except Exception as exc:
        return {"error": True, "message": f"Could not fetch balances: {exc}", "reasoning_chain": chain}

    annual = next(
        (b for b in balances
         if b.get("primary") or "annual" in (b.get("leaveType") or {}).get("name", "").lower()),
        None,
    )
    unused_days: float = float(annual.get("unused") or 0) if annual else 0.0

    if unused_days < _BALANCE_CONSERVATIVE:
        tier = "conservative"
    elif unused_days < _BALANCE_GENEROUS:
        tier = "balanced"
    else:
        tier = "generous"

    chain.append(
        f"Step 1 result: {unused_days:.0f} unused annual days → budget tier '{tier}'."
    )

    # Fetch holidays
    chain.append(f"Step 2: Loading Turkish public holidays for next {horizon_days} days.")
    horizon_end = today + timedelta(days=horizon_days)
    holidays = get_holidays(today, horizon_end)
    chain.append(f"Step 2 result: {len(holidays)} holiday(s) in window.")

    # Compute opportunities
    chain.append("Step 3: Scanning rest windows and ranking by efficiency.")
    opportunities = _scan_rest_opportunities(holidays, unused_days)
    chain.append(
        f"Step 3 result: Top {len(opportunities)} opportunity/ies returned."
    )

    return {
        "person_id": person_id,
        "annual_leave_remaining": unused_days,
        "budget_tier": tier,
        "horizon_days": horizon_days,
        "top_rest_opportunities": opportunities,
        "reasoning_chain": chain,
    }
