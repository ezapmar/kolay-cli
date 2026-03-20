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
def person_list(
    status: str = "active",
    search: str | None = None,
    match: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """[READ] List employees. Status: 'active'/'inactive'. search= API-side, match= client-side substring match on name/email. Returns {items, totalCount, page}."""
    result = person_svc.list_people(page=page, status=status, search=search, limit=limit)
    if match:
        result["items"] = filter_items_silent(
            result["items"], match,
            [
                lambda p: f"{p.get('firstName', '')} {p.get('lastName', '')}",
                lambda p: p.get("workEmail") or p.get("email") or "",
            ],
        )
    return result


@require_auth
def person_view(person_id: str) -> dict[str, Any]:
    """[READ] View full profile of an employee. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved)."""
    return person_svc.view_person(person_id)


@require_auth
def person_summary(person_id: str) -> dict[str, Any]:
    """[READ] View condensed summary of an employee. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved)."""
    return person_svc.summary(person_id)


@require_auth
def person_leave_status(person_id: str) -> list[dict[str, Any]]:
    """[READ] View leave balances for an employee. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved)."""
    return person_svc.leave_status(person_id)


@require_auth
def person_create(
    first_name: str,
    last_name: str,
    email: str,
    employment_start: str,
    mobile_phone: str | None = None,
) -> dict[str, Any]:
    """[WRITE] Create a new employee record. Dates in YYYY-MM-DD."""
    return person_svc.create_person(
        first_name=first_name, last_name=last_name,
        email=email, employment_start=employment_start,
        mobile_phone=mobile_phone,
    )


@require_auth
def person_update(
    person_id: str,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    mobile_phone: str | None = None,
    custom_fields: dict[str, str] | None = None,
    extra_fields: dict[str, str] | None = None,
) -> dict[str, Any]:
    """[WRITE] Update an employee's profile. Only supplied fields are changed. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved). Use extra_fields for raw API field names (e.g. {"department": "Engineering"}) not covered by the named parameters."""
    if extra_fields is not None:
        merged: dict[str, str] = dict(extra_fields)
        if first_name: merged["firstName"] = first_name
        if last_name: merged["lastName"] = last_name
        if email: merged["workEmail"] = email
        if mobile_phone: merged["mobilePhone"] = mobile_phone
        if not merged:
            return {"error": True, "message": "It looks like no fields were provided to update. Please specify at least one field to change."}
        return person_svc.update_person_fields(person_id, merged)
    return person_svc.update_person(
        person_id, first_name=first_name, last_name=last_name,
        email=email, mobile_phone=mobile_phone, custom_fields=custom_fields,
    )


@require_auth
def person_terminate(
    person_id: str,
    termination_date: str,
    reason_code: str,
) -> dict[str, Any]:
    """[DESTRUCTIVE] Terminate employee. Cannot be undone. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved). Dates in YYYY-MM-DD. Reason codes: '01' probation, '03' voluntary resignation (istifa), '04' termination without notice, '10' end of contract, '11' retirement, '22' employer termination, '23' death, '30' other."""
    return person_svc.terminate_person(person_id, termination_date=termination_date, reason_code=reason_code)


@require_auth
def person_rehire(person_id: str, start_date: str) -> dict[str, Any]:
    """[WRITE] Rehire a previously terminated employee. person_id: Employee ID (UUID, must be an inactive/terminated employee). Dates in YYYY-MM-DD."""
    return person_svc.rehire_person(person_id, start_date=start_date)


@require_auth
def person_update_fields(
    person_id: str,
    update_fields: dict[str, str],
) -> dict[str, Any]:
    """[WRITE] Update arbitrary fields on an employee profile using raw API field names (e.g. {"department": "Engineering"}). person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved)."""
    if not update_fields:
        return {"error": True, "message": "No fields provided to update."}
    return person_svc.update_person_fields(person_id, update_fields)


@require_auth
def employee_health_check(person_id: str) -> dict[str, Any]:
    """[READ] Unified cross-reference diagnostic tool.
    Returns an employee's upcoming leaves, recent timelogs, and training history in a single call.
    Helps prevent fragmented tool calls that hit rate limits or context windows.
    person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved)."""
    from datetime import date
    
    # 1. Base Info
    p_info = person_svc.view_person(person_id)
    
    # 2. Upcoming Leaves (only future approved leaves)
    today_str = date.today().isoformat()
    leaves = leave_svc.list_leaves(status="approved", person_id=person_id, start=today_str, limit=5)
    
    # 3. Recent Timelogs
    timelogs_res = timelog_svc.list_timelogs(person_id=person_id, limit=5)
    
    # 4. Training
    trainings = person_svc.list_trainings(person_id)

    return {
        "employee": p_info,
        "upcoming_leaves": leaves,
        "recent_timelogs": timelogs_res.get("items", []),
        "training_assignments": trainings
    }


@require_auth
def person_assign_training(
    person_id: str,
    training_id: str,
    status: str = "waiting",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """[WRITE] Assign training to employee. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved). training_id: UUID from training_list. Status: 'waiting' or 'approved'."""
    return person_svc.assign_training(
        person_id=person_id, training_id=training_id,
        status=status, start_date=start_date, end_date=end_date,
    )



@require_auth
def person_update_training(
    assignment_id: str,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """[WRITE] Update a training assignment. assignment_id: UUID from person_list_trainings. Status: 'waiting'/'approved'/'completed'. Dates in YYYY-MM-DD."""
    return person_svc.update_training(assignment_id, status=status, start_date=start_date, end_date=end_date)


@require_auth
def person_delete_training(assignment_id: str) -> dict[str, Any]:
    """[DESTRUCTIVE] Remove a training assignment from an employee. Cannot be undone. assignment_id: UUID from person_list_trainings."""
    return person_svc.delete_training(assignment_id)


def register(mcp):
    mcp.add_tool(Tool.from_function(person_list, annotations={"readOnlyHint": True, "openWorldHint": False}))
    mcp.add_tool(Tool.from_function(person_view, annotations={"readOnlyHint": True, "openWorldHint": False}))
    mcp.add_tool(Tool.from_function(person_summary, annotations={"readOnlyHint": True, "openWorldHint": False}))
    mcp.add_tool(Tool.from_function(person_leave_status, annotations={"readOnlyHint": True, "openWorldHint": False}))
    mcp.add_tool(Tool.from_function(person_create, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}))
    mcp.add_tool(Tool.from_function(person_update, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}))
    mcp.add_tool(Tool.from_function(person_terminate, annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}))
    mcp.add_tool(Tool.from_function(person_rehire, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}))
    mcp.add_tool(Tool.from_function(person_update_fields, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}))
    mcp.add_tool(Tool.from_function(employee_health_check, annotations={"readOnlyHint": True, "openWorldHint": False}))
    mcp.add_tool(Tool.from_function(person_assign_training, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}))
    mcp.add_tool(Tool.from_function(person_update_training, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}))
    mcp.add_tool(Tool.from_function(person_delete_training, annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}))
