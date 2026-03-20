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
def timelog_list(
    start: str | None = None,
    end: str | None = None,
    person_id: str | None = None,
    type: str | None = None,
    status: str | None = None,
    match: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """[READ] List timelogs. Types: 'work'/'overtime'/'remote'. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved; omit to list all). match= substring match on employee name or type."""
    result = timelog_svc.list_timelogs(
        start=start, end=end, person_id=person_id,
        type=type, status=status, page=page, limit=limit,
    )
    if match:
        result["items"] = filter_items_silent(
            result["items"], match,
            [
                lambda tl: f"{(tl.get('person') or {}).get('firstName', '')} {(tl.get('person') or {}).get('lastName', '')}",
                lambda tl: str(tl.get("type") or ""),
            ],
        )
    return result


@require_auth
def timelog_view(timelog_id: str) -> dict[str, Any]:
    """[READ] View timelog entry details."""
    return timelog_svc.view_timelog(timelog_id)


@require_auth
def timelog_create(
    person_id: str,
    start: str,
    end: str,
    type: str = "work",
    description: str = "",
) -> dict[str, Any]:
    """[WRITE] Create timelog. person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved). Start/End in YYYY-MM-DD HH:MM:SS. Types: 'work', 'overtime', 'remote'."""
    return timelog_svc.create_timelog(
        person_id=person_id, start=start, end=end,
        type=type, description=description,
    )


@require_auth
def timelog_delete(timelog_id: str) -> dict[str, Any]:
    """[DESTRUCTIVE] Permanently delete a timelog record. Cannot be undone."""
    return timelog_svc.delete_timelog(timelog_id)


def register(mcp):
    mcp.add_tool(timelog_list)
    mcp.add_tool(timelog_view)
    mcp.add_tool(timelog_create)
    mcp.add_tool(timelog_delete)
