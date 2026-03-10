from __future__ import annotations
from typing import Any
import typer
from rich.table import Table
from rich.tree import Tree

from ..api import KolayClient, APIError, safe_id
from ..services import unit as svc
from ..ui import (
    console, short_id, print_success, print_empty,
    api_call, no_command_help, PRIMARY,
    filter_items,
    is_json_mode, json_output, json_error,
)

app = typer.Typer(help="Manage organisational units (departments, locations, etc.) in Kolay.")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


def _render_unit_tree(node: dict, tree: Tree) -> None:
    """Recursively render a unit node and its children into a Rich Tree."""
    node_name = node.get("name", "—")
    node_id = str(node.get("id", ""))
    
    is_leaf = "children" not in node and "items" not in node
    label = f"[steel_blue1]{node_name}[/steel_blue1]" if is_leaf else f"[bold white]{node_name}[/bold white]"
    
    branch = tree.add(f"{label} [grey62]{short_id(node_id)}[/grey62]")
    
    for item in (node.get("items") or []):
        i_name = item.get("name", "—")
        i_id = str(item.get("id", ""))
        branch.add(f"[steel_blue1]{i_name}[/steel_blue1] [grey62]{short_id(i_id)}[/grey62]")
    
    for child in (node.get("children") or []):
        _render_unit_tree(child, branch)


@app.command(name="tree")
def show_unit_tree(
    filter: str | None = typer.Option(None, "--filter", "-f", help="Filter units/items by name"),
) -> None:
    """Show the full organisational unit tree (departments, locations, teams, etc.)."""
    with api_call("Fetching unit tree..."):
        nodes = svc.unit_tree()

    if is_json_mode():
        json_output(nodes)
        return
    if not nodes:
        print_empty("organisational units")
        return

    # ── Filter mode: flatten tree -> table ───────────────────────────────────
    if filter:
        flat: list[dict] = []

        def _collect_all(node: dict) -> None:
            flat.append({"name": node.get("name", "—"), "id": str(node.get("id", ""))})
            for item in (node.get("items") or []):
                flat.append({"name": item.get("name", "—"), "id": str(item.get("id", ""))})
            for child in (node.get("children") or []):
                _collect_all(child)

        for n in nodes:
            _collect_all(n)

        matched = filter_items(
            flat, filter,
            [lambda u: str(u.get("name") or "")],
            label="units",
        )

        console.print(f"\n[bold {PRIMARY}]Units matching '{filter}'[/bold {PRIMARY}]\n")
        tbl = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
        tbl.add_column("#", style="grey62", justify="right", width=4)
        tbl.add_column("Name", style="bold white", min_width=24)
        tbl.add_column("Short ID", style="grey62")
        for i, u in enumerate(matched, 1):
            tbl.add_row(str(i), u["name"], short_id(u["id"]))
        console.print(tbl)
        console.print()
        return

    # ── Normal tree mode ─────────────────────────────────────────────────────
    console.print(f"\n[bold {PRIMARY}]Organisational Unit Tree[/bold {PRIMARY}]\n")
    root = Tree(f"[bold {PRIMARY}]Company[/bold {PRIMARY}]")
    for node in nodes:
        _render_unit_tree(node, root)

    console.print(root)
    console.print()


@app.command(name="create-item")
def create_unit_item(
    unit_id: str | None = typer.Option(None, "--unit-id", help="ID of the unit to add the item to"),
    unit_name: str | None = typer.Option(None, "--unit-name", help="Name of the unit (e.g., Location)"),
    description: str | None = typer.Option(None, "--desc", help="Description of the new item"),
    item_name: str | None = typer.Option(None, "--name", "-n", help="Name of the new item (e.g., Amsterdam)"),
) -> None:
    """Create a new item inside an organisational unit.
    
    If no ID or names are provided, fetches the tree and lets you pick.
    """
    console.print(f"\n[bold {PRIMARY}]Create Unit Item[/bold {PRIMARY}]\n")

    if not unit_id or not unit_name:
        with api_call("Fetching unit tree..."):
            tree_data = svc.unit_tree()
        units_flat: list[dict[str, str]] = []

        def _collect(node: dict) -> None:
            nid = str(node.get("id", ""))
            if nid:
                units_flat.append({"id": nid, "name": node.get("name", "—")})
            for child in (node.get("children") or []):
                _collect(child)

        for n in tree_data:
            _collect(n)

        if not units_flat:
            from ..ui import print_error
            print_error("No organisational units found.", hint="Define units in Kolay first.")
            return

        console.print(f"[bold white]  Pick a unit:[/bold white]\n")
        tbl = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
        tbl.add_column("#", style="grey62", justify="right", width=4)
        tbl.add_column("Unit Name", style="bold white", min_width=22)
        tbl.add_column("Short ID", style="grey62")
        for i, u in enumerate(units_flat, 1):
            tbl.add_row(str(i), u["name"], short_id(u["id"]))
        console.print(tbl)
        console.print()

        raw = typer.prompt(" Pick a unit (# or ID)")
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(units_flat):
                unit_id, unit_name = units_flat[idx]["id"], units_flat[idx]["name"]
                console.print(f" [{PRIMARY}]Adding to [bold]{unit_name}[/bold][/{PRIMARY}]\n")
            else:
                unit_id = raw
        except ValueError:
            unit_id = raw

        if not unit_name:
            unit_name = typer.prompt(" Confirm unit name (e.g. Location)")

    if not item_name:
        item_name = typer.prompt(f" New item name for '{unit_name}'")

    with api_call(f"Adding '{item_name}' to {unit_name}..."):
        svc.create_unit_item(
            unit_id=unit_id, unit_name=unit_name,
            item_name=item_name, description=description,
        )

    print_success(f"'{item_name}' added to {unit_name} successfully.")
