from __future__ import annotations
from typing import Any
import typer
from rich.table import Table
from rich.panel import Panel

from ..api import KolayClient, safe_id
from ..services import training as svc
from ..ui import (
    console, short_id, print_success, print_empty, kv_table, pick_training,
    print_next_steps, print_pagination_footer,
    print_irreversible_warning,
    save_page_state, load_page_state,
    api_call, no_command_help, PRIMARY, filter_items,
    is_json_mode, is_yes_mode, json_output, json_error, require_arg, resolve_row, global_to_page_relative,
)

app = typer.Typer(help="Manage company training catalogue.")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


@app.command(name="list")
def list_trainings(
    search: str | None = typer.Option(None, "--search", "-s", help="Search by training name"),
    filter: str | None = typer.Option(None, "--filter", "-f", help="Filter locally by training name"),
    page: int = typer.Option(1, help="Page number"),
    limit: int = typer.Option(20, help="Number of records to return"),
) -> None:
    """List all trainings in the company catalogue."""
    with api_call("Fetching training catalogue..."):
        result = svc.list_trainings(search=search, page=page, limit=limit)

    items = result["items"]
    total = result["totalCount"]

    if is_json_mode():
        json_output(result)
        return
    if not items:
        print_empty("trainings")
        return

    items = filter_items(
        items, filter,
        [lambda tr: str(tr.get("name", ""))],
        label="trainings",
    )

    title = "Training Catalogue"
    if search:
        title += f" matching '{search}'"
    if filter:
        title += f" filtered by '{filter}'"

    console.print(f"\n[bold {PRIMARY}]{title}[/bold {PRIMARY}]\n")
    table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
    table.add_column("#", style="grey62", justify="right", width=4)
    table.add_column("Training Name", style="bold white", min_width=24)
    table.add_column("Duration", justify="right", style="grey85")
    table.add_column("Short ID", style="grey62")

    for i, tr in enumerate(items, 1):
        row_num = (page - 1) * limit + i
        dur = tr.get("duration") or tr.get("durationDays") or "—"
        table.add_row(str(row_num), str(tr.get("name", "—")), str(dur), short_id(str(tr.get("id", ""))))

    console.print(table)
    _extra = f"--search \"{search}\"" if search else ""
    print_pagination_footer(
        command="kolay training list",
        page=page, limit=limit, shown=len(items), total=total,
        extra_flags=_extra,
    )
    save_page_state(resource="training", page=page, limit=limit, total=total)
    print_next_steps([
        ("kolay training view <#>", "View training details"),
        ("kolay person assign-training", "Assign a training to an employee"),
        ("kolay training create", "Add a new training to the catalogue"),
    ])


def _resolve_training_id(value: str, *, limit: int = 50) -> str:
    """Resolve row number from `kolay training list` to a real training UUID.

    Honours the last-listed page and converts global row numbers to
    page-relative indices before resolving.
    """
    if not value.isdigit():
        return value
    state = load_page_state("training")
    if state and state["page"] > 1:
        page_rel = global_to_page_relative(int(value), page=state["page"], limit=state["limit"])
        result = svc.list_trainings(page=state["page"], limit=state["limit"])
        return resolve_row(str(page_rel), result.get("items", []), label="training")
    result = svc.list_trainings(limit=limit)
    return resolve_row(value, result.get("items", []), label="training")


@app.command(name="view")
def view_training(training_id: str | None = typer.Argument(None, help="ID or row number of the training to view")) -> None:
    """View full details of a specific training in the catalogue.

    Pass the UUID or row number from ``kolay training list`` (e.g. 1, 3).
    """
    require_arg(training_id, "training-id")
    if not training_id:
        training_id = pick_training()
    training_id = _resolve_training_id(training_id)

    with api_call("Fetching training details..."):
        data = svc.view_training(training_id)

    if is_json_mode():
        json_output(data)
        return
    name = data.get("name", "Training Details")
    console.print(f"\n[bold {PRIMARY}]Training[/bold {PRIMARY}] [bold white]{name}[/bold white]\n")
    console.print(Panel(kv_table(data, exclude=["id", "name"]), border_style=PRIMARY, expand=False))
    console.print()


@app.command(name="create")
def create_training(
    name: str | None = typer.Option(None, "--name", "-n", help="Training name"),
    description: str | None = typer.Option(None, "--desc", help="Training description"),
    duration: str | None = typer.Option(None, "--duration", help="Duration in days"),
) -> None:
    """Add a new training to the company catalogue."""
    console.print(f"\n[bold {PRIMARY}]Create Training[/bold {PRIMARY}]\n")

    if not name:
        if is_json_mode():
            require_arg(None, "name")
        name = typer.prompt(" Name")
    if not description:
        if not is_json_mode():
            description = typer.prompt(" Description (optional)", default="")
    if not duration:
        if not is_json_mode():
            duration = typer.prompt(" Duration in days (optional)", default="")

    with api_call(f"Adding '{name}'..."):
        result = svc.create_training(name=name, description=description or "", duration=duration or "")

    if is_json_mode():
        json_output(result)
    else:
        print_success("Training added to catalogue.")


@app.command(name="update")
def update_training(
    training_id: str | None = typer.Argument(None, help="ID of the training to update"),
    name: str | None = typer.Option(None, "--name", "-n", help="New name"),
    description: str | None = typer.Option(None, "--desc", help="New description"),
) -> None:
    """Update details for an existing training in the catalogue."""
    require_arg(training_id, "training-id")
    if not training_id:
        training_id = pick_training()
    training_id = _resolve_training_id(training_id)

    if not any([name, description]):
        # Fetch current to show as defaults for prompts
        with api_call("Fetching current training..."):
            cur = svc.view_training(training_id)
        if is_json_mode():
            require_arg(None, "name")
        name = typer.prompt(" Name", default=cur.get("name", ""))
        description = typer.prompt(" Description", default=cur.get("description") or "")

    with api_call("Saving changes..."):
        result = svc.update_training(training_id, name=name, description=description)

    if is_json_mode():
        json_output(result)
    else:
        print_success("Training updated successfully.")


@app.command(name="delete")
def delete_training(training_id: str | None = typer.Argument(None, help="ID of the training to delete")) -> None:
    """Permanently remove a training from the company catalogue."""
    require_arg(training_id, "training-id")
    if not training_id:
        training_id = pick_training()
    training_id = _resolve_training_id(training_id)

    with api_call("Fetching training name..."):
        data = svc.view_training(training_id)

    name = data.get("name", "this training")
    if not is_yes_mode():
        typer.confirm(f" Delete '{name}' and all associated history?", abort=True)

    with api_call("Deleting training..."):
        result = svc.delete_training(training_id)

    if is_json_mode():
        json_output(result)
    else:
        print_success("Training removed from catalogue.")
        print_irreversible_warning()
