from __future__ import annotations
import typer
from rich.table import Table

from ..services import approval as svc
from ..ui import (
    console, short_id, fmt_val, print_empty, api_call, no_command_help, PRIMARY,
    filter_items, is_json_mode, json_output,
)

app = typer.Typer(help="View approval processes configured in Kolay.")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


@app.command(name="list")
def list_approval_processes(
    filter: str | None = typer.Option(None, "--filter", "-f", help="Filter by process name or type"),
) -> None:
    """List all approval workflows configured for your company."""
    with api_call("Fetching approval processes..."):
        items = svc.list_approval_processes()

    if is_json_mode():
        json_output(items)
        return
    if not items:
        print_empty("approval processes")
        return

    items = filter_items(
        items, filter,
        [
            lambda ap: str(ap.get("name") or ""),
            lambda ap: str(ap.get("type") or ""),
        ],
        label="approval processes",
    )

    title = "Approval Processes"
    if filter:
        title += f" matching '{filter}'"
    console.print(f"\n[bold {PRIMARY}]{title}[/bold {PRIMARY}]\n")
    table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
    table.add_column("#", style="grey62", justify="right", width=4)
    table.add_column("Process Name", style="bold white", min_width=22)
    table.add_column("Type", style="grey85")
    table.add_column("Steps", justify="right")
    table.add_column("Short ID", style="grey62")

    for i, ap in enumerate(items, 1):
        steps = ap.get("steps", [])
        table.add_row(
            str(i),
            str(ap.get("name", "—")),
            str(ap.get("type", "—")),
            str(len(steps) if isinstance(steps, list) else 0),
            short_id(str(ap.get("id", "")))
        )

    console.print(table)
    console.print()
