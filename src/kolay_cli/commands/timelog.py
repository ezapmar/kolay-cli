from __future__ import annotations
from typing import Any
import typer
from rich.table import Table
from rich.panel import Panel
from datetime import datetime

from ..api import KolayClient, safe_id
from ..services import timelog as svc
from ..ui import (
    console, short_id, display_status, fmt_val,
    print_success, print_empty, kv_table, pick_timelog, pick_person,
    print_next_steps, print_pagination_footer,
    save_page_state, load_page_state,
    confirm_destructive_action, print_irreversible_warning,
    api_call, recoverable_api_call, no_command_help, PRIMARY,
    filter_items, validate_date, prompt_date, fmt_datetime,
    is_json_mode, is_yes_mode, json_output, json_error, require_arg, resolve_row, global_to_page_relative,
)

app = typer.Typer(help="Manage timelogs (work hours, overtime, etc.) in Kolay.")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


@app.command(name="list")
def list_timelogs(
    page: int = typer.Option(1, help="Page number"),
    limit: int = typer.Option(20, help="Number of records to return"),
    person_id: str | None = typer.Option(None, "--person-id", "-p", help="Filter by person ID"),
    type: str | None = typer.Option(None, "--type", "-t", help="Filter by type: work, overtime, remote"),
    status: str | None = typer.Option(None, "--status", help="Filter: waiting, approved, rejected"),
    start: str | None = typer.Option(None, "--start", help="Start date (YYYY-MM-DD)"),
    end: str | None = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
    filter: str | None = typer.Option(None, "--filter", "-f", help="Filter by employee name or type"),
) -> None:
    """List timelog records. Filterable by person, type, status, or date range."""
    with api_call("Fetching timelogs..."):
        result = svc.list_timelogs(
            start=start, end=end, person_id=person_id,
            type=type, status=status, page=page, limit=limit,
        )

    items = result["items"]
    total = result["totalCount"]

    if is_json_mode():
        json_output(result)
        return
    if not items:
        print_empty("timelog records")
        return

    items = filter_items(
        items, filter,
        [
            lambda tl: f"{(tl.get('person') or {}).get('firstName', '')} {(tl.get('person') or {}).get('lastName', '')}",
            lambda tl: str(tl.get("type") or ""),
        ],
        label="timelog records",
    )

    title = f"\u23f1\ufe0f Timelog Records"
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

    for i, tl in enumerate(items, 1):
        p = tl.get("person", {})
        pname = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() if isinstance(p, dict) else "—"
        table.add_row(
            str(i + (page - 1) * limit), pname,
            str(tl.get("type", "—")),
            fmt_datetime(tl.get("startDate")),
            fmt_datetime(tl.get("endDate")),
            display_status(str(tl.get("status", ""))),
            short_id(str(tl.get("id", "")))
        )

    console.print(table)
    _extra_parts = []
    if type:
        _extra_parts.append(f"--type {type}")
    if status:
        _extra_parts.append(f"--status {status}")
    print_pagination_footer(
        command="kolay timelog list",
        page=page, limit=limit, shown=len(items), total=total,
        extra_flags=" ".join(_extra_parts),
    )
    save_page_state(resource="timelog", page=page, limit=limit, total=total)
    print_next_steps([
        ("kolay timelog view <#>", "View timelog details"),
        ("kolay timelog create", "Submit a new timelog entry"),
        ("kolay timelog list --status waiting", "See pending approvals"),
    ])


def _resolve_timelog_id(value: str, *, limit: int = 50) -> str:
    """Resolve row number from `kolay timelog list` to a real timelog UUID.

    Honours the last-listed page and converts global row numbers to
    page-relative indices before resolving.
    """
    if not value.isdigit():
        return value
    state = load_page_state("timelog")
    if state and state["page"] > 1:
        page_rel = global_to_page_relative(int(value), page=state["page"], limit=state["limit"])
        result = svc.list_timelogs(page=state["page"], limit=state["limit"])
        return resolve_row(str(page_rel), result["items"], label="timelog")
    result = svc.list_timelogs(limit=limit)
    return resolve_row(value, result["items"], label="timelog")


@app.command(name="view")
def view_timelog(timelog_id: str | None = typer.Argument(None, help="ID or row number of the timelog to view")) -> None:
    """View full details and approval workflow for a specific timelog.

    Pass the UUID or row number from ``kolay timelog list`` (e.g. 1, 5).
    """
    require_arg(timelog_id, "timelog-id")
    if not timelog_id:
        timelog_id = pick_timelog()
    timelog_id = _resolve_timelog_id(timelog_id)

    with api_call("Fetching timelog details..."):
        data = svc.view_timelog(timelog_id)

    if is_json_mode():
        json_output(data)
        return
    p = data.get("person", {})
    pname = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() if isinstance(p, dict) else "Unknown"
    console.print(f"\n[bold {PRIMARY}]⏱️ Timelog[/bold {PRIMARY}] [bold white]{pname}[/bold white] — {data.get('type', 'Work')}")
    console.print(f"  {display_status(str(data.get('status', '')))}\n")
    console.print(Panel(kv_table(data, exclude=["id", "person", "type", "status", "personId"]), border_style=PRIMARY, expand=False))
    console.print()


@app.command(name="create")
def create_timelog(
    person_id: str | None = typer.Option(None, "--person-id", "-p", help="ID of the person"),
    type: str = typer.Option("work", "--type", "-t", help="Type: work, overtime, remote"),
    start: str | None = typer.Option(None, "--start", "-s", help="Start datetime (YYYY-MM-DD HH:MM:SS)"),
    end: str | None = typer.Option(None, "--end", "-e", help="End datetime (YYYY-MM-DD HH:MM:SS)"),
    description: str | None = typer.Option(None, "--desc", help="Optional description"),
) -> None:
    """Submit a new timelog entry for approval."""
    from ..api.errors import APIError
    console.print(f"\n[bold {PRIMARY}]⏱️ Create Timelog Entry[/bold {PRIMARY}]\n")

    require_arg(person_id, "person-id")
    if not person_id:
        person_id = pick_person()

    while True:
        if start:
            start = validate_date(start, "%Y-%m-%d %H:%M:%S")
        else:
            if is_json_mode():
                require_arg(None, "start")
            start = prompt_date("Start", default=datetime.now().replace(minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"), is_datetime=True)

        if end:
            end = validate_date(end, "%Y-%m-%d %H:%M:%S")
        else:
            if is_json_mode():
                require_arg(None, "end")
            end = prompt_date("End", is_datetime=True)

        try:
            with recoverable_api_call("Submitting timelog..."):
                result = svc.create_timelog(
                    person_id=person_id, start=start, end=end,
                    type=type, description=description or "",
                )

            if is_json_mode():
                json_output(result)
            else:
                print_success("Timelog entry submitted for approval.")
            break  # success

        except APIError as exc:
            msg = getattr(exc, "message", "")
            msg_lower = msg.lower()

            console.print()
            if "\xfcst \xfcste" in msg_lower or "overlap" in msg_lower or "conflict" in msg_lower:
                console.print(
                    "  [bold yellow]💡 Tip:[/bold yellow] These hours overlap with an existing timelog entry.\n"
                    "  Check your existing entries: [bold]kolay timelog list[/bold]"
                )
            elif "s\xfcre" in msg_lower or "duration" in msg_lower or "end" in msg_lower:
                console.print(
                    "  [bold yellow]💡 Tip:[/bold yellow] The end time must be after the start time."
                )

            console.print()
            console.print(f"  [cyan]1[/cyan]  Try different times")
            console.print(f"  [cyan]2[/cyan]  Abort")
            console.print()

            choice = typer.prompt("  Choose an option", default="2").strip()
            if choice == "1":
                start = None  # reset so the loop re-prompts
                end = None
            else:
                console.print("\n  [grey62]Aborted.[/grey62]\n")
                raise typer.Exit(1)


@app.command(name="delete")
def delete_timelog(timelog_id: str | None = typer.Argument(None, help="ID of the timelog to delete")) -> None:
    """Permanently delete a timelog record."""
    require_arg(timelog_id, "timelog-id")
    if not timelog_id:
        timelog_id = pick_timelog()
    timelog_id = _resolve_timelog_id(timelog_id)

    # 3.1: Fetch the record so we can show meaningful details in the prompt
    try:
        with api_call("Fetching timelog details..."):
            tl_data = svc.view_timelog(timelog_id)
        p = tl_data.get("person", {})
        emp = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() or short_id(timelog_id)
        tl_type = str(tl_data.get("type") or "—")
        start = fmt_datetime(tl_data.get("startDate"))
        end = fmt_datetime(tl_data.get("endDate"))
        period = f"{start} → {end}"

        confirm_destructive_action(
            action="Delete timelog record",
            details=[
                ("Employee", emp),
                ("Type", tl_type),
                ("Period", period),
                ("Status", str(tl_data.get("status") or "—")),
            ],
        )
    except Exception:
        # Fallback if fetch fails — still confirm with whatever we have
        if not is_yes_mode():
            typer.confirm("  Delete this timelog record?", abort=True)

    with api_call("Deleting timelog..."):
        result = svc.delete_timelog(timelog_id)

    if is_json_mode():
        json_output(result)
    else:
        print_success("Timelog deleted successfully.")
        print_irreversible_warning()
