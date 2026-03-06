"""Training catalogue services."""
from __future__ import annotations

from typing import Any

from ..api.client import KolayClient, safe_id


def list_trainings(
    *,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """Return ``{items, totalCount}``."""
    params: dict[str, Any] = {"page": page, "limit": limit}
    if search:
        params["search"] = search
    resp = KolayClient().get("v2/training/list", params=params)
    data = resp.get("data", {})
    items = data.get("items", []) if isinstance(data, dict) else []
    total = data.get("totalCount", 0) if isinstance(data, dict) else len(items)
    return {"items": items, "totalCount": total}


def view_training(training_id: str) -> dict[str, Any]:
    return KolayClient().get(f"v2/training/view/{safe_id(training_id)}").get("data", {})


def create_training(
    *,
    name: str,
    description: str = "",
    duration: str = "",
) -> dict[str, Any]:
    KolayClient().post("v2/training/create", data={
        "name": name, "description": description, "duration": duration,
    })
    return {"status": "created", "name": name}


def update_training(
    training_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    KolayClient().put(f"v2/training/update/{safe_id(training_id)}", data=payload)
    return {"status": "updated", "id": training_id}


def delete_training(training_id: str) -> dict[str, Any]:
    resp = KolayClient().get(f"v2/training/view/{safe_id(training_id)}")
    name = resp.get("data", {}).get("name", "")
    KolayClient().delete(f"v2/training/delete/{safe_id(training_id)}")
    return {"status": "deleted", "id": training_id, "name": name}
