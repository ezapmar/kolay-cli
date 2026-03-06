from __future__ import annotations
from typing import Any
import typer
from rich.table import Table
from rich.panel import Panel
from datetime import datetime, timedelta

from ..api import KolayClient, safe_id
from ..services import calendar as svc
from ..ui import (
    console, short_id, fmt_val, print_success, print_empty,
    pick_event, api_call, no_command_help, PRIMARY, filter_items,
    is_json_mode, is_yes_mode, json_output, json_error, resolve_row, require_arg,
)

app = typer.Typer(help="Manage calendar events in Kolay.")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


def _fmt_datetime(dt: str | None, fallback: str = "—") -> str:
    if not dt:
        return fallback
    try:
        return datetime.strptime(dt[:19], "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y  %H:%M")
    except ValueError:
        return dt


def _duration(start: str, end: str) -> str:
    try:
        s = datetime.strptime(start[:19], "%Y-%m-%d %H:%M:%S")
        e = datetime.strptime(end[:19], "%Y-%m-%d %H:%M:%S")
        total_minutes = int((e - s).total_seconds() // 60)
        if total_minutes < 60:
            return f"{total_minutes}m"
        h, m = divmod(total_minutes, 60)
        return f"{h}h {m}m" if m else f"{h}h"
    except (ValueError, TypeError, AttributeError):
        return "—"


@app.command(name="list")
def list_events(
    search: str | None = typer.Option(None, "--search", "-s", help="Search by title keyword"),
    filter: str | None = typer.Option(None, "--filter", "-f", help="Filter locally by title"),
    start: str | None = typer.Option(None, "--start", help="Filter start date (YYYY-MM-DD). Defaults to today."),
    end: str | None = typer.Option(None, "--end", help="Filter end date (YYYY-MM-DD). Defaults to +30 days."),
    page: int = typer.Option(1, "--page", help="Page number"),
    limit: int = typer.Option(20, "--limit", help="Number of records to return"),
) -> None:
    """List your calendar events for a given period. Defaults to the next 30 days."""
    with api_call(f"Fetching events..."):
        result = svc.list_events(start=start, end=end, search=search, page=page, limit=limit)

    items = result["items"]
    total = result["totalCount"]

    if is_json_mode():
        json_output(result)
        return
    if not items:
        print_empty("events", hint="Try --start 2000-01-01 to see past events.")
        return

    items = filter_items(
        items, filter,
        [lambda ev: str(ev.get("title", ""))],
        label="events",
    )

    now = datetime.now()
    label_start = start or now.strftime("%Y-%m-%d")
    label_end = end or (now + timedelta(days=30)).strftime("%Y-%m-%d")

    title = "📅 Calendar Events"
    if search:
        title += f" matching '{search}'"
    if filter:
        title += f" filtered by '{filter}'"

    console.print(f"\n[bold {PRIMARY}]{title}[/bold {PRIMARY}] [grey62]({label_start} → {label_end})[/grey62]\n")
    table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
    table.add_column("#", style="grey62", width=4, justify="right")
    table.add_column("Title", style="bold white", min_width=24)
    table.add_column("Start", style="grey85")
    table.add_column("Duration", style="grey62", justify="right")
    table.add_column("Short ID", style="grey62")

    for i, event in enumerate(items, 1):
        ev_start, ev_end = event.get("start", ""), event.get("end", "")
        table.add_row(
            str(i), str(event.get("title", "—")),
            _fmt_datetime(ev_start), _duration(ev_start, ev_end),
            short_id(str(event.get("id", "")))
        )

    console.print(table)
    console.print()


def _resolve_event_id(value: str, *, limit: int = 50) -> str:
    """Resolve row number from `kolay calendar list` to a real event UUID."""
    if not value.isdigit():
        return value
    result = svc.list_events(limit=limit)
    items = result["items"]
    if not items:
        # Fallback: broader date range
        from ..api.client import KolayClient as _C
        items = _C().get("v2/event/list", params={"limit": limit}).get("data", [])
    return resolve_row(value, items, label="event")


@app.command(name="view")
def view_event(event_id: str | None = typer.Argument(None, help="ID or row number of the event to view")) -> None:
    """View full details of a specific calendar event.

    Pass the UUID or row number from ``kolay calendar list`` (e.g. 1, 3).
    """
    if not event_id:
        event_id = pick_event()
    event_id = _resolve_event_id(event_id)

    with api_call("Fetching event details..."):
        data = svc.view_event(event_id)

    title = data.get("title", "—")
    ev_start, ev_end = data.get("start", ""), data.get("end", "")

    console.print(f"\n[bold {PRIMARY}]📅 Event[/bold {PRIMARY}] [bold white]{title}[/bold white]\n")
    tbl = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    tbl.add_column("Key", style="grey85", min_width=12)
    tbl.add_column("Value")
    tbl.add_row("Start", _fmt_datetime(ev_start))
    tbl.add_row("End", _fmt_datetime(ev_end))
    tbl.add_row("Duration", _duration(ev_start, ev_end))
    tbl.add_row("Comment", fmt_val(data.get("comment")))
    tbl.add_row("ID", f"[grey62]{data.get('id', '—')}[/grey62]")
    console.print(Panel(tbl, border_style=PRIMARY, expand=False))
    console.print()


@app.command(name="create")
def create_event(
    title: str | None = typer.Option(None, "--title", "-t", help="Event title"),
    start: str | None = typer.Option(None, "--start", "-s", help="Start datetime (YYYY-MM-DD HH:MM:SS)"),
    end: str | None = typer.Option(None, "--end", "-e", help="End datetime (YYYY-MM-DD HH:MM:SS)"),
    comment: str | None = typer.Option(None, "--comment", "-c", help="Optional description"),
) -> None:
    """Create a new calendar event. Prompts for missing fields."""
    console.print(f"\n[bold {PRIMARY}]📅 Create Calendar Event[/bold {PRIMARY}]\n")

    if not title:
        title = typer.prompt("  Title")
    if not start:
        start = typer.prompt("  Start (YYYY-MM-DD HH:MM:SS)", default=datetime.now().replace(minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"))
    if not end:
        try:
            default_end = (datetime.strptime(start[:19], "%Y-%m-%d %H:%M:%S") + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            default_end = start
        end = typer.prompt("  End (YYYY-MM-DD HH:MM:SS)", default=default_end)

    with api_call(f"Creating event '{title}'..."):
        resp = svc.create_event(title=title, start=start, end=end, comment=comment or "")

    new_id = resp.get("id", "—")
    print_success(f"Event created!  [grey62]…{str(new_id)[-8:]}  {title}  {start[:10]}  {start[11:16]}  ({_duration(start, end)})[/grey62]")


@app.command(name="update")
def update_event(
    event_id: str | None = typer.Argument(None, help="ID of the event to update"),
    title: str | None = typer.Option(None, "--title", "-t", help="New title"),
    start: str | None = typer.Option(None, "--start", "-s", help="New start datetime"),
    end: str | None = typer.Option(None, "--end", "-e", help="New end datetime"),
    comment: str | None = typer.Option(None, "--comment", "-c", help="New comment"),
) -> None:
    """Update an existing calendar event."""
    if not event_id:
        event_id = pick_event()
    event_id = _resolve_event_id(event_id)

    if not any([title, start, end, comment]):
        with api_call("Fetching current event..."):
            cur = svc.view_event(event_id)
        title = typer.prompt("  Title", default=cur.get("title", ""))
        start = typer.prompt("  Start", default=cur.get("start", ""))
        end = typer.prompt("  End", default=cur.get("end", ""))
        comment = typer.prompt("  Comment", default=cur.get("comment") or "")

    with api_call("Saving changes..."):
        svc.update_event(event_id, title=title, start=start, end=end, comment=comment)

    print_success("Event updated successfully.")


@app.command(name="delete")
def delete_event(event_id: str | None = typer.Argument(None, help="ID of the event to delete")) -> None:
    """Permanently delete a calendar event."""
    if not event_id:
        event_id = pick_event()
    event_id = _resolve_event_id(event_id)

    with api_call("Fetching event..."):
        data = svc.view_event(event_id)

    title = data.get("title", "this event")
    if not is_yes_mode():
        typer.confirm(f"  Delete '{title}'?", abort=True)

    with api_call("Deleting event..."):
        svc.delete_event(event_id)

    print_success("Event deleted successfully.")
