from __future__ import annotations

import typer
from rich.panel import Panel
from datetime import date

from ..api.client import KolayClient
from ..security import require_auth
from ..ui import console, api_call, PRIMARY

def run_status() -> None:
    """Print a compact dashboard of your current HR status."""
    from ..services.person import leave_status
    from ..services.nudge import analyze_pending_work
    from ..services.turkish_holidays import get_holidays
    
    with api_call("Loading dashboard..."):
        client = KolayClient()
        response = client.get("v2/profile/me")
        data = response.get("data", {})
        person_id = data.get("id")

        name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
        dept = (data.get('department') or {}).get("name", "")
        title = data.get("title", "")
        org_info = dept if dept else title

        # Leave Balance
        try:
            balances = leave_status(person_id) if person_id else []
            annual = next(
                (b for b in balances
                 if b.get("primary") or "annual" in (b.get("leaveType") or {}).get("name", "").lower()),
                None,
            )
            unused_days = float(annual.get("unused") or 0) if annual else 0.0
            leave_str = f"{unused_days:g} days remaining"
            leave_raw = unused_days
        except Exception:
            leave_str = "Unavailable"
            leave_raw = 0.0

        # Pending Approvals
        try:
            pending = analyze_pending_work()
            pending_count = len(pending)
            pending_str = str(pending_count)
        except Exception:
            pending_str = "Unavailable"
            pending_count = 0

        # Next Holiday
        try:
            today = date.today()
            yr = today.year
            holidays = get_holidays(date(yr, 1, 1), date(yr + 1, 12, 31), try_gcal=False)
            future_holidays = sorted([(d, name) for d, name in holidays.items() if d >= today])
            if future_holidays:
                next_d, next_name = future_holidays[0]
                delta = (next_d - today).days
                in_days = f" (in {delta} days)" if delta > 0 else " (Today!)"
                holiday_str = f"{next_d.strftime('%b %d')} - {next_name}{in_days}"
            else:
                holiday_str = "None found"
            
            holiday_raw = future_holidays[0][0].isoformat() if future_holidays else None
        except Exception:
            holiday_str = "Unavailable"
            holiday_raw = None

    from ..ui.output import is_json_mode, json_output
    if is_json_mode():
        json_output({
            "name": name,
            "org_info": org_info,
            "leave_balance_days": leave_raw,
            "pending_items": pending_count,
            "next_holiday": holiday_raw,
        })
        return

    content = (
        f"You:             [bold white]{name}[/bold white]{f' ({org_info})' if org_info else ''}\n"
        f"Leave Balance:   [bold]{leave_str}[/bold]\n"
        f"Pending Work:    [bold]{pending_str}[/bold] items\n"
        f"Next Holiday:    [bold]{holiday_str}[/bold]\n"
    )

    console.print()
    console.print(Panel(
        content,
        title=f"[bold {PRIMARY}]kolay status[/bold {PRIMARY}]",
        border_style=PRIMARY,
        expand=False,
        padding=(1, 3)
    ))
    console.print()
