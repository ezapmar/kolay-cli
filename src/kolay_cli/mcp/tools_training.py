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
def training_list(
    search: str | None = None,
    match: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """[READ] List trainings in catalogue. search= API-side, match= client-side substring match on name."""
    result = training_svc.list_trainings(search=search, page=page, limit=limit)
    if match:
        result["items"] = filter_items_silent(
            result["items"], match,
            [lambda tr: str(tr.get("name", ""))],
        )
    return result


@require_auth
def training_view(training_id: str) -> dict[str, Any]:
    """[READ] View training details."""
    return training_svc.view_training(training_id)


@require_auth
def training_create(name: str, description: str = "", duration: str = "") -> dict[str, Any]:
    """[WRITE] Add training to the company catalogue. Duration is a string (e.g. '3 days')."""
    return training_svc.create_training(name=name, description=description, duration=duration)


async def training_delete(training_id: str, ctx: Context) -> dict[str, Any]:
    """[DESTRUCTIVE] Permanently remove training from the company catalogue and all assignment history. Cannot be undone."""
    from ..security import resolve_token, validate_token, _auth_error
    from ..rate_limiter import token_key as rl_token_key
    from ..activity_log import log_tool_call
    import time as _time

    token = resolve_token()
    if not token:
        return _auth_error("It seems we need a valid API token to proceed.",
                           hint="Please run 'kolay auth login' to get started.")
    status = validate_token(token)
    if not status:
        return _auth_error(f"We couldn't verify the current session: {status.reason}",
                           hint="Please run 'kolay auth login' to refresh your connection.")

    # Look up the training so we can name it in the confirmation prompt
    try:
        training = training_svc.view_training(training_id)
        display = training.get("name", training_id)
    except Exception:
        display = training_id

    # Human-in-the-loop confirmation
    try:
        result = await ctx.elicit(
            f"CONFIRM DELETE: Permanently remove training '{display}' and ALL assignment history? This cannot be undone.",
            response_type=bool,
        )
        if result.action != "accept" or not result.data:
            return {"cancelled": True, "message": f"Deletion of '{display}' was not confirmed. No changes made."}
    except Exception:
        return {
            "error": True,
            "message": (
                f"Deleting '{display}' requires explicit confirmation, but this client "
                "does not support interactive prompts. Re-call with confirm=True to proceed."
            ),
        }

    key = rl_token_key(token)
    t0 = _time.monotonic()
    try:
        res = training_svc.delete_training(training_id)
        log_tool_call(key, "training_delete", {"training_id": training_id}, _time.monotonic() - t0, success=True)
        return res
    except Exception as exc:
        log_tool_call(key, "training_delete", {}, _time.monotonic() - t0, success=False, error=str(exc))
        from ..api.errors import APIError
        if isinstance(exc, APIError) and exc.status_code == 401:
            return _auth_error("It seems the API session has expired.",
                               hint="Please run 'kolay auth login' to update your connection.")
        raise


@require_auth
def training_update(
    training_id: str,
    name: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """[WRITE] Update a training in the catalogue. Only supplied fields are changed."""
    return training_svc.update_training(training_id, name=name, description=description)


@require_auth
def person_training_manage(
    action: str,
    person_id: str | None = None,
    training_id: str | None = None,
    assignment_id: str | None = None,
    status: str = "waiting",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """[WRITE] Unified tool to assign, update, or remove training from an employee.
    action: 'assign' (requires person_id, training_id), 'update' (requires assignment_id), or 'remove' (requires assignment_id).
    Status: 'waiting', 'approved', or 'completed'. Dates in YYYY-MM-DD.
    """
    if action == "assign":
        if not person_id or not training_id:
            return {"error": True, "message": "action='assign' requires person_id and training_id"}
        return person_svc.assign_training(
            person_id=person_id, training_id=training_id,
            status=status, start_date=start_date, end_date=end_date,
        )
    elif action == "update":
        if not assignment_id:
            return {"error": True, "message": "action='update' requires assignment_id"}
        return person_svc.update_training(
            assignment_id, status=status, start_date=start_date, end_date=end_date
        )
    elif action == "remove":
        if not assignment_id:
            return {"error": True, "message": "action='remove' requires assignment_id"}
        return person_svc.delete_training(assignment_id)

    return {"error": True, "message": "Invalid action. Use 'assign', 'update', or 'remove'."}


@require_auth
def person_list_trainings(person_id: str) -> list[dict[str, Any]]:
    """[READ] List training assignments for an employee. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved). Returns the employee's training history and pending assignments."""
    return person_svc.list_trainings(person_id)


def register(mcp):
    mcp.add_tool(Tool.from_function(training_list, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
    mcp.add_tool(Tool.from_function(training_view, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
    mcp.add_tool(Tool.from_function(training_create, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
        tags={"write"},
    ))
    mcp.add_tool(Tool.from_function(training_update, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
        tags={"write"},
    ))
    mcp.add_tool(Tool.from_function(training_delete, annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
        tags={"destructive", "admin"},
    ))
    mcp.add_tool(Tool.from_function(person_training_manage, annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
        tags={"write"},
    ))
    mcp.add_tool(Tool.from_function(person_list_trainings, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
