from .adapter import Tool, Context
from typing import Any
from ..security import require_auth, McpAuthError
from ..services import person as person_svc
from ..services import leave as leave_svc
from ..services import timelog as timelog_svc
from ..services import training as training_svc
from ..ui.search import filter_items_silent


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



def _inline_auth() -> str:
    """Shared auth check for async tools that bypass @require_auth.

    Raises McpAuthError on failure so FastMCP signals is_error=True.
    Returns the valid token on success.
    """
    from ..security import resolve_token, validate_token
    token = resolve_token()
    if not token:
        raise McpAuthError(
            "No API token found. Authentication is required to call this tool.",
            hint="Run 'kolay auth login' or set the KOLAY_API_TOKEN environment variable.",
        )
    status = validate_token(token)
    if not status:
        raise McpAuthError(
            f"The current session could not be verified: {status.reason}",
            hint="Run 'kolay auth login' to refresh your connection.",
        )
    return token


async def person_view(person_id: str, ctx: Context) -> dict[str, Any]:
    """[READ] View full profile of an employee. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved). Automatically caches this person as 'last_person' in session state."""
    _inline_auth()  # raises McpAuthError on failure

    result = person_svc.view_person(person_id)

    # Auto-cache: store last-viewed person for convenient cross-tool reuse
    try:
        name = f"{result.get('firstName', '')} {result.get('lastName', '')}".strip()
        await ctx.set_state("last_person_id", result.get("id", person_id))
        await ctx.set_state("last_person_name", name)
        if email := result.get("workEmail") or result.get("email"):
            await ctx.set_state("last_person_email", email)
    except Exception:
        pass  # State caching is best-effort — never break the main result

    return result


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


async def person_terminate(
    person_id: str,
    termination_date: str,
    reason_code: str,
    ctx: Context,
) -> dict[str, Any]:
    """[DESTRUCTIVE] Terminate employee. Cannot be undone. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved). Dates in YYYY-MM-DD. Reason codes: '01' probation, '03' voluntary resignation (istifa), '04' termination without notice, '10' end of contract, '11' retirement, '22' employer termination, '23' death, '30' other."""
    from ..rate_limiter import token_key as rl_token_key
    from ..activity_log import log_tool_call
    import time as _time

    token = _inline_auth()  # raises McpAuthError on failure

    # Look up the person so we can show their name in the confirmation prompt
    try:
        person = person_svc.view_person(person_id)
        display = f"{person.get('firstName', '')} {person.get('lastName', '')}".strip() or person_id
    except Exception:
        display = person_id

    # Human-in-the-loop confirmation via elicitation
    try:
        result = await ctx.elicit(
            f"CONFIRM TERMINATION: Permanently terminate {display} on {termination_date} "
            f"(reason code {reason_code})? This action cannot be undone.",
            response_type=bool,
        )
        if result.action != "accept" or not result.data:
            return {"cancelled": True, "message": f"Termination of {display} was not confirmed. No changes made."}
    except Exception:
        # Client does not support elicitation — require the caller to re-confirm via a flag
        return {
            "error": True,
            "message": (
                f"Termination of {display} requires explicit confirmation, but this client "
                "does not support interactive prompts. Re-call with confirm=True to proceed."
            ),
        }

    key = rl_token_key(token)
    t0 = _time.monotonic()
    try:
        res = person_svc.terminate_person(person_id, termination_date=termination_date, reason_code=reason_code)
        log_tool_call(key, "person_terminate", {"person_id": person_id, "termination_date": termination_date, "reason_code": reason_code}, _time.monotonic() - t0, success=True)
        return res
    except Exception as exc:
        log_tool_call(key, "person_terminate", {}, _time.monotonic() - t0, success=False, error=str(exc))
        from ..api.errors import APIError
        if isinstance(exc, APIError) and exc.error_code == "invalid_credentials":
            raise McpAuthError(
                exc.message,
                hint=exc.hint,
                code=exc.status_code or 401,
            ) from exc
        raise


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
    mcp.add_tool(Tool.from_function(person_list, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
    mcp.add_tool(Tool.from_function(person_view, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
    mcp.add_tool(Tool.from_function(person_summary, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
    mcp.add_tool(Tool.from_function(person_leave_status, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
    mcp.add_tool(Tool.from_function(person_create, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
        tags={"write"},
    ))
    mcp.add_tool(Tool.from_function(person_update, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
        tags={"write"},
    ))
    mcp.add_tool(Tool.from_function(person_terminate, annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
        tags={"destructive", "admin"},
    ))
    mcp.add_tool(Tool.from_function(person_rehire, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
        tags={"write"},
    ))
    mcp.add_tool(Tool.from_function(person_update_fields, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
        tags={"write"},
    ))
    mcp.add_tool(Tool.from_function(employee_health_check, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
    mcp.add_tool(Tool.from_function(person_assign_training, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
        tags={"write"},
    ))
    mcp.add_tool(Tool.from_function(person_update_training, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
        tags={"write"},
    ))
    mcp.add_tool(Tool.from_function(person_delete_training, annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
        tags={"destructive"},
    ))
