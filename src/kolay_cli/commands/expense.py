from __future__ import annotations
import typer
from rich.table import Table

from ..services import expense as svc
from ..ui import (
    console, short_id, print_empty,
    api_call, no_command_help, PRIMARY,
    filter_items,
    is_json_mode, json_output, json_error, SUCCESS, ERROR,
)

app = typer.Typer(help="Manage expense categories in Kolay.")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


@app.command(name="categories")
def list_categories(
    title: str | None = typer.Option(None, "--title", "-t", help="Filter by title"),
    enabled_only: bool = typer.Option(False, "--enabled", help="Show only enabled categories"),
    filter: str | None = typer.Option(None, "--filter", "-f", help="Filter locally by category title"),
) -> None:
    """List expense categories available for your company."""
    with api_call("Fetching expense categories..."):
        data = svc.list_categories(title=title, enabled_only=enabled_only)

    if is_json_mode():
        json_output(data)
        return
    if not data:
        print_empty("expense categories")
        return

    data = filter_items(
        data, filter,
        [lambda c: c.get("title") or c.get("name") or ""],
        label="expense categories",
    )

    title_hdr = "🧾 Expense Categories"
    if filter:
        title_hdr += f" matching '{filter}'"
    console.print(f"\n[bold {PRIMARY}]{title_hdr}[/bold {PRIMARY}]\n")
    table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
    table.add_column("#", style="grey62", justify="right", width=4)
    table.add_column("Title", style="bold white", min_width=20)
    table.add_column("Enabled", justify="center")
    table.add_column("Short ID", style="grey62")

    for i, cat in enumerate(data, 1):
        enabled = cat.get("isEnable") or cat.get("enabled")
        enabled_str = f"[{SUCCESS}]Yes[/{SUCCESS}]" if enabled else f"[{ERROR}]No[/{ERROR}]"
        table.add_row(str(i), cat.get("title") or cat.get("name") or "—", enabled_str, short_id(str(cat.get("id", ""))))

    console.print(table)
    console.print()
