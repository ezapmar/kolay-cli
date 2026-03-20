from fastmcp.tools import Tool
from typing import Any
from fastmcp.server.context import Context
from fastmcp.dependencies import CurrentContext
from ..security import require_auth
from ..services import person as person_svc
from ..services import leave as leave_svc
from ..services import timelog as timelog_svc
from ..services import training as training_svc
from ..services import transaction as transaction_svc
from ..services import calendar as calendar_svc
from ..services import unit as unit_svc
from ..services import approval as approval_svc
from ..services import hr_analytics as hr_analytics_svc
from ..services import payroll as payroll_svc
from ..services import wellness as wellness_svc
from ..ui.search import filter_items_silent
from ..mcp_progress import sync_progress_bridge
import json


@require_auth
def transaction_list(
    person_id: str | None = None,
    type: str | None = None,
    status: str | None = None,
    match: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """[READ] List transactions. Types: 'expense'/'bonus'/'advancePayment'/'premium'/'otherCut'. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved; omit to list all). match= substring match on employee name or type."""
    result = transaction_svc.list_transactions(
        person_id=person_id, type=type, status=status,
        page=page, limit=limit,
    )
    if match:
        result["items"] = filter_items_silent(
            result["items"], match,
            [
                lambda trx: f"{(trx.get('person') or {}).get('firstName', '')} {(trx.get('person') or {}).get('lastName', '')}",
                lambda trx: str(trx.get("type") or ""),
            ],
        )
    return result


@require_auth
def transaction_view(transaction_id: str) -> dict[str, Any]:
    """[READ] View transaction details."""
    return transaction_svc.view_transaction(transaction_id)


@require_auth
def transaction_create(
    person_id: str,
    type: str,
    amount: float,
    date: str,
    currency: str = "TL",
    description: str = "",
) -> dict[str, Any]:
    """[WRITE] Create transaction. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved). Types: 'expense', 'bonus', 'advancePayment', 'premium', 'otherCut'. Dates in YYYY-MM-DD."""
    return transaction_svc.create_transaction(
        person_id=person_id, type=type, amount=amount,
        date=date, currency=currency, description=description,
    )


@require_auth
def transaction_delete(transaction_id: str) -> dict[str, Any]:
    """[DESTRUCTIVE] Permanently delete a transaction record. Cannot be undone."""
    return transaction_svc.delete_transaction(transaction_id)


@require_auth
def payroll_sheet_view(
    payroll_id: str,
    search: str | None = None,
    status: list[str] | None = None,
    salary_period: list[str] | None = None,
    match: str | None = None,
) -> dict[str, Any]:
    """[READ] View payroll sheet (Çarşaf Bordro) for a payroll run. Returns the full payroll data as JSON. payroll_id: UUID of the payroll run. search= filter by employee name, status= e.g. ['ended','active'], salary_period= e.g. ['monthly']. match= client-side substring match on employee names in results. Required scope: payroll-sheet:view."""
    result = payroll_svc.view_payroll_sheet(
        payroll_id,
        search=search,
        status=status,
        salary_period=salary_period,
    )
    if filter and isinstance(result, dict):
        items = result.get("items", [])
        if items:
            result["items"] = filter_items_silent(
                items, match,
                [
                    lambda row: f"{(row.get('person') or row.get('employee') or {}).get('firstName', '')} {(row.get('person') or row.get('employee') or {}).get('lastName', '')}",
                    lambda row: (row.get('person') or row.get('employee') or {}).get('name', ''),
                ],
            )
    return result


def register(mcp):
    mcp.add_tool(Tool.from_function(transaction_list, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
    mcp.add_tool(Tool.from_function(transaction_view, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
    mcp.add_tool(Tool.from_function(transaction_create, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
        tags={"write"},
    ))
    mcp.add_tool(Tool.from_function(transaction_delete, annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
        tags={"destructive"},
    ))
    mcp.add_tool(Tool.from_function(payroll_sheet_view, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
