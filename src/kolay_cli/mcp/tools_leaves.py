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
def leave_list(
    status: str = "approved",
    start: str | None = None,
    end: str | None = None,
    person_id: str | None = None,
    match: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """[READ] List leave records. Status: 'approved'/'waiting'/'rejected'/'cancelled'. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved; omit to list all). match= substring match on employee name or leave type."""
    items = leave_svc.list_leaves(status=status, start=start, end=end, person_id=person_id, limit=limit)
    if match:
        items = filter_items_silent(
            items, match,
            [
                lambda lv: (lv.get("person") or {}).get("name") or "",
                lambda lv: (lv.get("leaveType") or {}).get("name") or "",
            ],
        )
    return items


@require_auth
def leave_view(leave_id: str) -> dict[str, Any]:
    """[READ] View details of a leave record."""
    return leave_svc.view_leave(leave_id)


@require_auth
def leave_create(
    person_id: str,
    leave_type_id: str,
    start_date: str,
    end_date: str,
    comment: str = "",
) -> dict[str, Any]:
    """[WRITE] Submit a leave request. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved). Dates in YYYY-MM-DD."""
    return leave_svc.create_leave(
        person_id=person_id, leave_type_id=leave_type_id,
        start_date=start_date, end_date=end_date, comment=comment,
    )


@require_auth
def leave_cancel(leave_id: str) -> dict[str, Any]:
    """[DESTRUCTIVE] Cancel a leave request. Only 'waiting' or 'approved' leaves can be cancelled. leave_id: UUID from leave_list."""
    return leave_svc.cancel_leave(leave_id)


@require_auth
def analyze_leave_impact(person_id: str, leave_type_id: str, requested_days: float) -> dict[str, Any]:
    """[READ] [DRY-RUN] Calculates how a requested leave will affect the user's future balance before actually creating it.
    LLM instructions: Always run this before `leave_create` or `request_time_off` to ensure the user has enough balance and to ask for explicit confirmation from the user (gaining user trust)."""
    balances = person_svc.leave_status(person_id)
    for b in balances:
        if str(b.get("leaveTypeId", "")) == str(leave_type_id):
            current_unused = b.get("unused", 0)
            new_unused = current_unused - requested_days
            return {
                "safe_to_proceed": new_unused >= 0,
                "leave_type": b.get("leaveType", {}).get("name", "Unknown"),
                "current_unused_days": current_unused,
                "requested_days": requested_days,
                "projected_unused_days": new_unused,
                "warning": "Insufficient balance!" if new_unused < 0 else None
            }
    return {"error": True, "message": "Leave type balance not found for this user."}



@require_auth
def leave_types(person_id: str) -> str:
    """[READ] View leave balances."""
    import json
    from ..services.person import leave_status
    balances = leave_status(person_id)
    if not balances:
        return json.dumps([])
    
    result = []
    for b in balances:
        name = b.get("leaveType", {}).get("name", "Unknown")
        result.append({
            "leave_type_id": b.get("leaveTypeId"),
            "name": name,
            "total": b.get("total"),
            "used": b.get("used"),
            "unused": b.get("unused"),
            "isPaid": b.get("isPaid"),
        })
    return json.dumps(result)


def register(mcp):
    mcp.resource("kolay://leave-types/{person_id}")(leave_types)

    mcp.add_tool(Tool.from_function(leave_list, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
    mcp.add_tool(Tool.from_function(leave_view, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
    mcp.add_tool(Tool.from_function(leave_create, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
        tags={"write"},
    ))
    mcp.add_tool(Tool.from_function(leave_cancel, annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
        tags={"destructive"},
    ))
    mcp.add_tool(Tool.from_function(analyze_leave_impact, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
