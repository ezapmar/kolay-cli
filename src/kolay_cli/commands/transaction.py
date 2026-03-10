from __future__ import annotations
from typing import Any
import typer
from rich.table import Table
from rich.panel import Panel
from datetime import datetime

from ..api import KolayClient, safe_id
from ..services import transaction as svc
from ..services.transaction import TRANSACTION_TYPES
from ..ui import (
    console, short_id, display_status, fmt_num,
    print_success, print_empty, kv_table, print_next_steps, print_pagination_footer,
    save_page_state, load_page_state,
    confirm_destructive_action, print_irreversible_warning,
    pick_person, pick_transaction, api_call, recoverable_api_call, no_command_help, PRIMARY,
    filter_items, validate_date, prompt_date, fmt_datetime,
    is_json_mode, is_yes_mode, json_output, json_error, resolve_row, require_arg, global_to_page_relative,
)

app = typer.Typer(help="Manage financial transactions (expenses, bonuses, advances).")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


@app.command(name="list")
def list_transactions(
    page: int = typer.Option(1, help="Page number"),
    person_id: str | None = typer.Option(None, "--person-id", "-p", help="Filter by person ID"),
    type: str | None = typer.Option(None, "--type", "-t", help="Filter by type (expense, bonus, etc.)"),
    status: str | None = typer.Option(None, "--status", help="Filter by status (waiting, approved)"),
    filter: str | None = typer.Option(None, "--filter", "-f", help="Filter by employee name or type"),
    limit: int = typer.Option(20, help="Number of records to return"),
) -> None:
    """List financial transactions. Filterable by person, type, or approval status."""
    with api_call("Fetching transactions..."):
        result = svc.list_transactions(
            person_id=person_id, type=type, status=status,
            page=page, limit=limit,
        )

    items = result["items"]
    total = result["totalCount"]

    if is_json_mode():
        json_output(result)
        return
    if not items:
        print_empty("transactions")
        return

    items = filter_items(
        items, filter,
        [
            lambda trx: f"{(trx.get('person') or {}).get('firstName', '')} {(trx.get('person') or {}).get('lastName', '')}",
            lambda trx: str(trx.get("type") or ""),
        ],
        label="transactions",
    )

    title = " Transactions"
    if filter:
        title += f" matching '{filter}'"
    console.print(f"\n[bold {PRIMARY}]{title}[/bold {PRIMARY}]\n")
    table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
    table.add_column("#", style="grey62", justify="right", width=4)
    table.add_column("Employee", style="bold white", min_width=18)
    table.add_column("Type", style="grey85")
    table.add_column("Amount", justify="right", style="bold white")
    table.add_column("Status", justify="center", min_width=14)
    table.add_column("Short ID", style="grey62")

    for i, trx in enumerate(items, 1):
        p = trx.get("person", {})
        pname = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() if isinstance(p, dict) else "—"
        amt = trx.get("amount") or trx.get("totalAmount") or "—"
        curr = trx.get("currency", "")
        amt_str = f"{fmt_num(amt)} {curr}".strip()
        table.add_row(
            str(i + (page - 1) * limit), pname,
            str(trx.get("type", "—")), amt_str,
            display_status(str(trx.get("status", ""))),
            short_id(str(trx.get("id", "")))
        )

    console.print(table)
    _extra_parts = []
    if type:
        _extra_parts.append(f"--type {type}")
    if status:
        _extra_parts.append(f"--status {status}")
    print_pagination_footer(
        command="kolay transaction list",
        page=page, limit=limit, shown=len(items), total=total,
        extra_flags=" ".join(_extra_parts),
    )
    save_page_state(resource="transaction", page=page, limit=limit, total=total)
    print_next_steps([
        ("kolay transaction view <#>", "View transaction details"),
        ("kolay transaction create", "Create a new transaction (bonus, expense…)"),
        ("kolay transaction list --status waiting", "See pending approvals"),
    ])


def _resolve_transaction_id(value: str, *, limit: int = 50) -> str:
    """Resolve row number from `kolay transaction list` to a real UUID.

    Honours the last-listed page and converts global row numbers to
    page-relative indices before resolving.
    """
    if not value.isdigit():
        return value
    state = load_page_state("transaction")
    if state and state["page"] > 1:
        page_rel = global_to_page_relative(int(value), page=state["page"], limit=state["limit"])
        result = svc.list_transactions(page=state["page"], limit=state["limit"])
        return resolve_row(str(page_rel), result["items"], label="transaction")
    result = svc.list_transactions(limit=limit)
    return resolve_row(value, result["items"], label="transaction")


@app.command(name="view")
def view_transaction(transaction_id: str | None = typer.Argument(None, help="ID or row number of the transaction")) -> None:
    """View full details and notes of a specific transaction.

    Pass the UUID or row number from ``kolay transaction list`` (e.g. 1, 3).
    """
    require_arg(transaction_id, "transaction-id")
    if not transaction_id:
        transaction_id = pick_transaction()
    transaction_id = _resolve_transaction_id(transaction_id)

    with api_call("Fetching transaction details..."):
        data = svc.view_transaction(transaction_id)

    p = data.get("person", {})
    pname = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() if isinstance(p, dict) else "Unknown"
    console.print(f"\n[bold {PRIMARY}]Transaction[/bold {PRIMARY}] [bold white]{pname}[/bold white] — {data.get('type', 'Record')}")
    console.print(f" {display_status(str(data.get('status', '')))}\n")
    console.print(Panel(kv_table(data, exclude=["id", "person", "type", "status", "personId"]), border_style=PRIMARY, expand=False))
    console.print()


@app.command(name="create")
def create_transaction(
    person_id: str | None = typer.Option(None, "--person-id", "-p", help="ID of the person"),
    type: str | None = typer.Option(None, "--type", "-t", help="Type (expense, bonus, etc.)"),
    amount: float | None = typer.Option(None, "--amount", help="Total amount"),
    currency: str = typer.Option("TL", "--currency", help="Currency code"),
    date: str | None = typer.Option(None, "--date", help="Date (YYYY-MM-DD)"),
    description: str | None = typer.Option(None, "--desc", help="Optional description"),
) -> None:
    """Create a new financial transaction (bonus, cut, or expense)."""
    from ..api.errors import APIError
    console.print(f"\n[bold {PRIMARY}]New Transaction[/bold {PRIMARY}]\n")

    if not person_id:
        person_id = pick_person()
    if not type:
        console.print(" [bold white]Types:[/bold white] " + ", ".join(TRANSACTION_TYPES))
        type = typer.prompt(" Pick a type", default="expense")
    if amount is None:
        amount = float(typer.prompt(" Amount"))
    if amount < 0:
        console.print(" [yellow] Negative amount \u2014 did you mean a deduction (otherCut)?[/yellow]")
    if date:
        date = validate_date(date)
    else:
        date = prompt_date("Date", default=datetime.now().strftime("%Y-%m-%d"))

    while True:
        try:
            with recoverable_api_call("Submitting transaction..."):
                svc.create_transaction(
                    person_id=person_id, type=type, amount=amount,
                    currency=currency, date=date, description=description or "",
                )
            print_success("Transaction created successfully.")
            break
        except APIError as exc:
            msg = getattr(exc, "message", "").lower()

            console.print()
            if "amount" in msg or "miktar" in msg or "tutar" in msg:
                console.print(
                    " [bold yellow]Tip:[/bold yellow] The amount may be invalid for this transaction type."
                )
            elif "date" in msg or "tarih" in msg:
                console.print(
                    " [bold yellow]Tip:[/bold yellow] The transaction date may be outside the allowed period."
                )

            console.print()
            console.print(f" [cyan]1[/cyan]  Try a different amount")
            console.print(f" [cyan]2[/cyan]  Try a different date")
            console.print(f" [cyan]3[/cyan]  Abort")
            console.print()

            choice = typer.prompt(" Choose an option", default="3").strip()
            if choice == "1":
                amount = float(typer.prompt(" New amount", default=str(amount)))
            elif choice == "2":
                date = prompt_date("New date", default=date)
            else:
                console.print("\n  [grey62]Aborted.[/grey62]\n")
                raise typer.Exit(1)


@app.command(name="delete")
def delete_transaction(transaction_id: str | None = typer.Argument(None, help="ID of the transaction")) -> None:
    """Permanently delete a transaction record."""
    if not transaction_id:
        transaction_id = pick_transaction()
    transaction_id = _resolve_transaction_id(transaction_id)

    # 3.2: Fetch the record so the user sees what they're deleting
    try:
        with api_call("Fetching transaction details..."):
            trx_data = svc.view_transaction(transaction_id)
        p = trx_data.get("person", {})
        emp = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() if isinstance(p, dict) else "—"
        trx_type = str(trx_data.get("type") or "—")
        amt = trx_data.get("amount") or trx_data.get("totalAmount") or "—"
        curr = trx_data.get("currency", "")
        amt_str = f"{fmt_num(amt)} {curr}".strip() if amt != "—" else "—"
        trx_date = fmt_datetime(str(trx_data.get("date") or trx_data.get("createdAt") or "—"))
        status = str(trx_data.get("status") or "—")

        confirm_destructive_action(
            action="Delete transaction record",
            details=[
                ("Employee", emp),
                ("Type", trx_type),
                ("Amount", amt_str),
                ("Date", trx_date),
                ("Status", status),
            ],
        )
    except Exception:
        if not is_yes_mode():
            typer.confirm(" Delete this transaction?", abort=True)

    with api_call("Deleting transaction..."):
        svc.delete_transaction(transaction_id)

    print_success("Transaction deleted successfully.")
    print_irreversible_warning()
