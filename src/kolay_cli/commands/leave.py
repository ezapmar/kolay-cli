from __future__ import annotations
from typing import Any
import typer
from rich.table import Table
from rich.panel import Panel
from datetime import datetime

from ..api import KolayClient, safe_id
from ..services import leave as svc
from ..ui import (
    console, short_id, display_status, print_error, print_success, print_empty,
    kv_table, print_next_steps, print_pagination_footer,
    save_page_state, load_page_state,
    pick_person, pick_leave, api_call, recoverable_api_call, no_command_help, PRIMARY, SUCCESS,
    filter_items, validate_date, prompt_date, fmt_datetime,
    is_json_mode, is_yes_mode, json_output, json_error, resolve_row, require_arg,
)

app = typer.Typer(help="Manage leave records in Kolay.")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


@app.command(name="list")
def list_leaves(
    status: str = typer.Option("approved", help="Filter: approved, waiting, rejected, cancelled"),
    start: str | None = typer.Option(None, "--start", help="Start date (YYYY-MM-DD)"),
    end: str | None = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
    person_id: str | None = typer.Option(None, "--person-id", "-p", help="Filter by person ID"),
    filter: str | None = typer.Option(None, "--filter", "-f", help="Filter by employee name or leave type"),
    limit: int = typer.Option(50, help="Max records to return"),
) -> None:
    """List leave records. Defaults to approved leaves within the current year."""
    with api_call(f"Fetching {status} leave records..."):
        data = svc.list_leaves(status=status, start=start, end=end, person_id=person_id, limit=limit)

    if is_json_mode():
        json_output(data)
        return
    if not data:
        print_empty(f"{status} leave records")
        return

    data = filter_items(
        data, filter,
        [
            lambda lv: (lv.get("person") or {}).get("name") or "",
            lambda lv: (lv.get("leaveType") or {}).get("name") or "",
        ],
        label="leave records",
    )

    title = f"\U0001f3d6\ufe0f {status.title()} Leave Records"
    if filter:
        title += f" matching '{filter}'"
    console.print(f"\n[bold {PRIMARY}]{title}[/bold {PRIMARY}]\n")
    table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
    table.add_column("#", style="grey62", justify="right", width=4)
    table.add_column("Employee", style="bold white", min_width=18)
    table.add_column("Type", style="grey85")
    table.add_column("Start", style="grey62")
    table.add_column("End", style="grey62")
    table.add_column("Status", justify="center", min_width=14)
    table.add_column("Short ID", style="grey62")

    for i, lv in enumerate(data, 1):
        p = lv.get("person", {})
        ltype = lv.get("leaveType", {})
        table.add_row(
            str(i),
            p.get("name") or "—",
            ltype.get("name") or "—",
            fmt_datetime(lv.get("startDate")),
            fmt_datetime(lv.get("endDate")),
            display_status(str(lv.get("status", ""))),
            short_id(str(lv.get("id", "")))
        )

    console.print(table)
    # Leave API doesn't expose a server-side total — use limit-hit as proxy
    _leave_total = limit + 1 if len(data) == limit else len(data)
    _extra = f"--status {status}"
    print_pagination_footer(
        command="kolay leave list",
        page=0, limit=limit, shown=len(data), total=_leave_total,
        extra_flags=_extra,
    )
    save_page_state(resource="leave", page=1, limit=limit, total=len(data))
    print_next_steps([
        ("kolay leave view <#>", "View leave details"),
        ("kolay leave create", "Submit a new leave request"),
        ("kolay leave list --status waiting", "See pending approvals"),
    ])

    if not is_json_mode():
        try:
            from ..services import nudge as nudge_svc
            from ..ui.nudge_formatters import print_cross_service_nudge
            pending = nudge_svc.analyze_pending_work()
            if pending:
                print_cross_service_nudge(pending, "leave")
        except Exception:
            pass


def _resolve_leave_id(value: str, *, status: str = "approved", limit: int = 50) -> str:
    """Resolve row number from `kolay leave list` to a real leave UUID.

    Leave is limit-only (no pagination), so page state just validates the
    limit used — falls back to the default limit when no state is found.
    """
    if not value.isdigit():
        return value
    state = load_page_state("leave")
    effective_limit = state["limit"] if state else limit
    items = svc.list_leaves(status=status, limit=effective_limit)
    return resolve_row(value, items, label="leave record")


@app.command(name="view")
def view_leave(leave_id: str | None = typer.Argument(None, help="ID or row number of the leave record")) -> None:
    """View full details and workflow status of an individual leave record.

    Pass the UUID or row number from ``kolay leave list`` (e.g. 1, 3).
    """
    require_arg(leave_id, "leave-id")
    if not leave_id:
        leave_id = pick_leave()
    leave_id = _resolve_leave_id(leave_id)

    with api_call("Fetching leave details..."):
        data = svc.view_leave(leave_id)

    if is_json_mode():
        json_output(data)
        return

    p = data.get("person", {})
    ltype = data.get("leaveType", {})
    console.print(f"\n[bold {PRIMARY}]🏖️ Leave Record[/bold {PRIMARY}] [bold white]{p.get('name', 'Unknown')}[/bold white] — {ltype.get('name', 'Leave')}")
    console.print(f"  {display_status(str(data.get('status', '')))}\n")
    console.print(Panel(kv_table(data, exclude=["id", "person", "leaveType", "status", "personId", "leaveTypeId"]), border_style=PRIMARY, expand=False))
    console.print()


@app.command(name="create")
def create_leave(
    person_id: str | None = typer.Option(None, "--person-id", "-p", help="Person ID to create leave for"),
    leave_type_id: str | None = typer.Option(None, "--type-id", "-t", help="Leave type ID"),
    start_date: str | None = typer.Option(None, "--start", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
    comment: str | None = typer.Option(None, "--comment", "-c", help="Optional comment"),
) -> None:
    """Create a new leave request. Prompts for missing details interactively."""
    from ..api.errors import APIError
    from datetime import datetime as _dt
    console.print(f"\n[bold {PRIMARY}]🏖️ Create Leave Request[/bold {PRIMARY}]\n")

    if not person_id:
        person_id = pick_person()

    with api_call("Fetching available leave types..."):
        from ..services.person import leave_status
        if not leave_type_id:
            types = leave_status(person_id)
        else:
            types = []

    if not leave_type_id:
        if not types:
            print_error("This employee has no leave types assigned.")
            return
        console.print(f"\n  [bold white]Available Leave Types:[/bold white]")
        for i, t in enumerate(types, 1):
            l_obj = t.get("leaveType", {})
            console.print(f"  [{PRIMARY}]{i}[/{PRIMARY}]: {l_obj.get('name')}  [grey62]({t.get('unused', 0)} days left)[/grey62]")
        try:
            idx = int(typer.prompt("\n  Pick a leave type (#)", default="1")) - 1
            selected = types[idx]
            leave_type_id = str(selected.get("leaveTypeId", ""))
            sel_name = selected.get("leaveType", {}).get("name", "Unknown")
            sel_remaining = selected.get("unused", "?")
            console.print(f"  [{PRIMARY}]→ Selected: {sel_name}[/{PRIMARY}]\n")
        except (ValueError, IndexError):
            print_error("Invalid selection.")
            return
    else:
        sel_name = leave_type_id
        sel_remaining = "?"

    if start_date:
        start_date = validate_date(start_date)
    else:
        start_date = prompt_date("Start date", default=_dt.now().strftime("%Y-%m-%d"))

    if end_date:
        end_date = validate_date(end_date)
    else:
        from datetime import timedelta
        start_dt = _dt.strptime(start_date[:10], "%Y-%m-%d")
        # 5.4: Default to start_date + 1 weekday for Annual Leaves
        default_end = start_date[:10]
        if "yıllık" in sel_name.lower() or "annual" in sel_name.lower():
            days_to_add = 3 if start_dt.weekday() == 4 else 1 # skip weekend if Friday
            default_end = (start_dt + timedelta(days=days_to_add)).strftime("%Y-%m-%d")
            
        end_date = prompt_date("End date", default=default_end)

    while True:
        try:
            with recoverable_api_call("Submitting leave request..."):
                svc.create_leave(
                    person_id=person_id, leave_type_id=leave_type_id,
                    start_date=start_date, end_date=end_date,
                    comment=comment or "",
                )
            print_success("Leave request submitted successfully.")
            break
        except APIError as exc:
            msg = getattr(exc, "message", "")
            msg_lower = msg.lower()

            console.print()
            if "bakiye" in msg_lower or "balance" in msg_lower or "gün" in msg_lower or "insufficient" in msg_lower:
                console.print(
                    f"  [bold yellow]💡 Tip:[/bold yellow] Insufficient leave balance for [bold]{sel_name}[/bold].\n"
                    f"  Remaining: [bold]{sel_remaining}[/bold] days.\n"
                    "  Check the requested date range and try again."
                )
            elif "üst üste" in msg_lower or "overlap" in msg_lower or "dates" in msg_lower:
                console.print(
                    f"  [bold yellow]💡 Tip:[/bold yellow] The requested dates overlap with an existing leave request.\n"
                    "  Check your current leave records: [bold]kolay leave list[/bold]"
                )

            console.print()
            console.print(f"  [cyan]1[/cyan]  Try different dates")
            console.print(f"  [cyan]2[/cyan]  Check leave balance for this employee")
            console.print(f"  [cyan]3[/cyan]  Abort")
            console.print()

            choice = typer.prompt("  Choose an option", default="3").strip()
            if choice == "1":
                start_date = prompt_date("New start date", default=start_date)
                end_date = prompt_date("New end date", default=end_date)
                # loop again
            elif choice == "2":
                with api_call("Fetching leave balances..."):
                    from ..services.person import leave_status as _ls
                    balances = _ls(person_id)
                if balances:
                    for b in balances:
                        ltype = (b.get("leaveType") or {}).get("name", "—")
                        console.print(
                            f"  [grey85]{ltype}[/grey85]:  "
                            f"[orange1]{b.get('used', 0)} used[/orange1]  "
                            f"[bold green]{b.get('unused', 0)} remaining[/bold green]"
                        )
                    console.print()
                else:
                    console.print("  [grey62]No balance info found.[/grey62]\n")
                # Loop again after showing balances
            else:
                console.print("\n  [grey62]Aborted.[/grey62]\n")
                raise typer.Exit(1)
