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
def calendar_list(
    start: str | None = None,
    end: str | None = None,
    search: str | None = None,
    match: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """[READ] List calendar events. Dates YYYY-MM-DD. search= API-side, match= client-side substring match on title."""
    result = calendar_svc.list_events(start=start, end=end, search=search, page=page, limit=limit)
    if match:
        result["items"] = filter_items_silent(
            result["items"], match,
            [lambda ev: str(ev.get("title") or "")],
        )
    return result


@require_auth
def calendar_view(event_id: str) -> dict[str, Any]:
    """[READ] View event details."""
    return calendar_svc.view_event(event_id)


@require_auth
def calendar_create(
    title: str,
    start: str,
    end: str,
    comment: str = "",
) -> dict[str, Any]:
    """[WRITE] Create calendar event. Dates in YYYY-MM-DD HH:MM:SS."""
    return calendar_svc.create_event(title=title, start=start, end=end, comment=comment)


@require_auth
def calendar_update(
    event_id: str,
    title: str | None = None,
    start: str | None = None,
    end: str | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    """[WRITE] Update calendar event. Only supplied fields are changed."""
    return calendar_svc.update_event(event_id, title=title, start=start, end=end, comment=comment)


@require_auth
def calendar_delete(event_id: str) -> dict[str, Any]:
    """[DESTRUCTIVE] Permanently delete a calendar event. Cannot be undone."""
    return calendar_svc.delete_event(event_id)


@require_auth
def unit_tree(match: str | None = None) -> list[dict[str, Any]]:
    """[READ] Return organisational unit tree. match= substring match on unit/item name (returns flat list when filtering)."""
    nodes = unit_svc.unit_tree()
    if not filter:
        return nodes
    # Flatten tree for filtering
    flat: list[dict[str, Any]] = []
    def _collect(node: dict) -> None:
        flat.append({"name": node.get("name", ""), "id": str(node.get("id", ""))})
        for item in (node.get("items") or []):
            flat.append({"name": item.get("name", ""), "id": str(item.get("id", ""))})
        for child in (node.get("children") or []):
            _collect(child)
    for n in nodes:
        _collect(n)
    return filter_items_silent(flat, match, [lambda u: str(u.get("name") or "")])


@require_auth
def approval_list(match: str | None = None) -> list[dict[str, Any]]:
    """[READ] List approval workflows. match= substring match on process name or type."""
    items = approval_svc.list_approval_processes()
    if match:
        items = filter_items_silent(
            items, match,
            [
                lambda ap: str(ap.get("name") or ""),
                lambda ap: str(ap.get("type") or ""),
            ],
        )
    return items


def register(mcp):
    mcp.add_tool(calendar_list)
    mcp.add_tool(calendar_view)
    mcp.add_tool(calendar_create)
    mcp.add_tool(calendar_update)
    mcp.add_tool(calendar_delete)
    mcp.add_tool(unit_tree)
    mcp.add_tool(approval_list)
