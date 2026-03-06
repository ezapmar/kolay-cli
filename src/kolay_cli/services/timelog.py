"""Timelog services."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ..api.client import KolayClient, safe_id


def list_timelogs(
    *,
    start: str | None = None,
    end: str | None = None,
    person_id: str | None = None,
    type: str | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """Return ``{items, totalCount, page}``."""
    year = str(datetime.now().year)
    payload: dict[str, Any] = {
        "page": page, "limit": limit,
        "startDate": (start or f"{year}-01-01") + " 00:00:00",
        "endDate": (end or f"{year}-12-31") + " 23:59:59",
        "sortType": "startDate", "sortOrder": "desc",
    }
    if person_id:
        payload["personId"] = person_id
    if type:
        payload["type"] = type
    if status:
        payload["status"] = status
    resp = KolayClient().post("v2/timelog/list", data=payload)
    data = resp.get("data", {})
    items = data.get("items", []) if isinstance(data, dict) else []
    total = data.get("totalCount", 0) if isinstance(data, dict) else len(items)
    return {"items": items, "totalCount": total, "page": page}


def view_timelog(timelog_id: str) -> dict[str, Any]:
    return KolayClient().get(f"v2/timelog/view/{safe_id(timelog_id)}").get("data", {})


def create_timelog(
    *,
    person_id: str,
    start: str,
    end: str,
    type: str = "work",
    description: str = "",
) -> dict[str, Any]:
    KolayClient().post("v2/timelog/create", data={
        "personId": safe_id(person_id),
        "startDate": start,
        "endDate": end,
        "type": type,
        "status": "waiting",
        "description": description,
    })
    return {"status": "created", "person_id": person_id, "start": start, "end": end}


def delete_timelog(timelog_id: str) -> dict[str, Any]:
    KolayClient().delete(f"v2/timelog/delete/{safe_id(timelog_id)}")
    return {"status": "deleted", "id": timelog_id}
