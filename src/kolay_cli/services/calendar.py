"""Calendar/event services."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ..api.client import KolayClient, safe_id


def list_events(
    *,
    start: str | None = None,
    end: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """Return ``{items, totalCount, page}``."""
    now = datetime.now()
    start_dt = (start or now.strftime("%Y-%m-%d")) + " 00:00:00"
    end_dt = (end or (now + timedelta(days=30)).strftime("%Y-%m-%d")) + " 23:59:59"
    params: dict[str, Any] = {"start": start_dt, "end": end_dt, "page": page, "limit": limit}
    if search:
        params["search"] = search
    resp = KolayClient().get("v2/event/list", params=params)
    data = resp.get("data", {})
    items = data.get("items", []) if isinstance(data, dict) else []
    total = data.get("totalCount", 0) if isinstance(data, dict) else len(items)
    return {"items": items, "totalCount": total, "page": page}


def view_event(event_id: str) -> dict[str, Any]:
    return KolayClient().get(f"v2/event/view/{safe_id(event_id)}").get("data", {})


def create_event(
    *,
    title: str,
    start: str,
    end: str,
    comment: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"title": title, "start": start, "end": end}
    if comment:
        payload["comment"] = comment
    return KolayClient().post("v2/event/create", data=payload).get("data", {})


def update_event(
    event_id: str,
    *,
    title: str | None = None,
    start: str | None = None,
    end: str | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    cur = view_event(event_id)
    payload: dict[str, Any] = {
        "title": title or cur.get("title"),
        "start": start or cur.get("start"),
        "end": end or cur.get("end"),
        "comment": comment if comment is not None else cur.get("comment"),
    }
    KolayClient().put(f"v2/event/update/{safe_id(event_id)}", data=payload)
    return {"status": "updated", "id": event_id}


def delete_event(event_id: str) -> dict[str, Any]:
    KolayClient().delete(f"v2/event/delete/{safe_id(event_id)}")
    return {"status": "deleted", "id": event_id}
