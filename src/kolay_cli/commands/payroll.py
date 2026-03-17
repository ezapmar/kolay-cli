from __future__ import annotations

from typing import Any

import typer
from rich.table import Table
from rich.panel import Panel

from ..services import payroll as svc
from ..ui import (
    console, short_id, display_status, fmt_num,
    print_empty, kv_table, print_next_steps,
    api_call, no_command_help, PRIMARY,
    filter_items,
    is_json_mode, json_output, require_arg,
)

app = typer.Typer(help="View payroll sheets (Çarşaf Bordro).")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


@app.command(name="view")
def view_payroll_sheet(
    payroll_id: str | None = typer.Argument(None, help="UUID of the payroll run"),
    search: str | None = typer.Option(None, "--search", "-s", help="Filter by employee name (API-side)"),
    status: list[str] | None = typer.Option(None, "--status", help="Filter by status (e.g. ended, active)"),
    salary_period: list[str] | None = typer.Option(None, "--salary-period", help="Filter by salary period (e.g. monthly)"),
    filter: str | None = typer.Option(None, "--filter", "-f", help="Client-side substring match on employee names"),
) -> None:
    """View the payroll sheet (Çarşaf Bordro) for a specific payroll run.

    Pass the UUID of a payroll run to retrieve the full sheet data.
    Required API scope: payroll-sheet:view.
    """
    require_arg(payroll_id, "payroll-id")
    if not payroll_id:
        console.print(f"\n[bold {PRIMARY}]Payroll Sheet Viewer[/bold {PRIMARY}]\n")
        console.print("  [grey62]Tip: Find payroll run IDs in the Kolay IK dashboard → Payroll → Payroll Runs[/grey62]\n")
        payroll_id = typer.prompt("  Payroll run ID")

    with api_call("Fetching payroll sheet..."):
        result = svc.view_payroll_sheet(
            payroll_id,
            search=search,
            status=status or None,
            salary_period=salary_period or None,
        )

    if is_json_mode():
        json_output(result)
        return

    if not result:
        print_empty("payroll data")
        return

    # If the result contains items, display as a table
    items = result.get("items", []) if isinstance(result, dict) else []

    if filter and items:
        items = filter_items(
            items, filter,
            [
                lambda row: f"{(row.get('person') or row.get('employee') or {}).get('firstName', '')} {(row.get('person') or row.get('employee') or {}).get('lastName', '')}",
                lambda row: (row.get("person") or row.get("employee") or {}).get("name", ""),
            ],
            label="payroll rows",
        )

    if items:
        title = "Payroll Sheet"
        if search:
            title += f" (search: '{search}')"
        if filter:
            title += f" matching '{filter}'"
        console.print(f"\n[bold {PRIMARY}] {title}[/bold {PRIMARY}]")
        console.print(f"  [grey62]{len(items)} employee(s) · ID {short_id(payroll_id)}[/grey62]\n")

        table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
        table.add_column("#", style="grey62", justify="right", width=4)
        table.add_column("Employee", style="bold white", min_width=18)
        table.add_column("Gross", justify="right", style="bold white")
        table.add_column("Net", justify="right", style="bold white")
        table.add_column("Status", justify="center", min_width=14)
        table.add_column("Short ID", style="grey62")

        for i, row in enumerate(items, 1):
            p = row.get("person") or row.get("employee") or {}
            name = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip()
            if not name:
                name = p.get("name", "—")
            gross = row.get("gross") or row.get("grossSalary") or "—"
            net = row.get("net") or row.get("netSalary") or "—"
            gross_str = fmt_num(gross) if gross != "—" else "—"
            net_str = fmt_num(net) if net != "—" else "—"
            status_val = display_status(str(row.get("status", "—")))
            row_id = str(row.get("id") or row.get("personId") or "")

            table.add_row(str(i), name, gross_str, net_str, status_val, short_id(row_id))

        console.print(table)
        console.print()
    else:
        # No items — display as a panel of key-value pairs
        console.print(f"\n[bold {PRIMARY}] Payroll Sheet[/bold {PRIMARY}]")
        console.print(f"  [grey62]ID {short_id(payroll_id)}[/grey62]\n")
        if isinstance(result, dict) and result:
            console.print(Panel(kv_table(result), border_style=PRIMARY, expand=False))
        else:
            print_empty("payroll rows for this run")

    print_next_steps([
        ("kolay payroll view <id> --search 'name'", "Search within a payroll run"),
        ("kolay payroll view <id> --filter 'name'", "Client-side filter on results"),
        ("kolay --json payroll view <id>", "Export payroll data as JSON"),
    ])
