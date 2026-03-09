"""Leave services."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ..api.client import KolayClient, safe_id


def list_leaves(
    *,
    status: str = "approved",
    start: str | None = None,
    end: str | None = None,
    person_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    year = str(datetime.now().year)
    params: dict[str, Any] = {
        "status": status,
        "startDate": (start or f"{year}-01-01") + " 00:00:00" if not (start and len(start) > 10) else start,
        "endDate": (end or f"{year}-12-31") + " 23:59:59" if not (end and len(end) > 10) else end,
        "limit": limit,
    }
    if person_id:
        params["personId"] = safe_id(person_id, "person_id")
    return KolayClient().get("v2/leave/list", params=params).get("data", [])


def view_leave(leave_id: str) -> dict[str, Any]:
    return KolayClient().get(f"v2/leave/view/{safe_id(leave_id)}").get("data", {})


def create_leave(
    *,
    person_id: str,
    leave_type_id: str,
    start_date: str,
    end_date: str,
    comment: str = "",
) -> dict[str, Any]:
    sd = start_date + " 09:00:00" if len(start_date) == 10 else start_date
    ed = end_date + " 18:00:00" if len(end_date) == 10 else end_date
    KolayClient().post("v2/leave/create", data={
        "personId": safe_id(person_id),
        "leaveTypeId": safe_id(leave_type_id),
        "startDate": sd,
        "endDate": ed,
        "comment": comment,
    })
    return {"status": "created", "person_id": person_id, "start": start_date, "end": end_date}
