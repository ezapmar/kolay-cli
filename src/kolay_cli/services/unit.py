"""Organisation unit services."""
from __future__ import annotations

from typing import Any

from ..api.client import KolayClient, safe_id


def unit_tree() -> list[dict[str, Any]]:
    data = KolayClient().get("v2/unit/show-unit-tree").get("data", [])
    return data if isinstance(data, list) else [data]


def create_unit_item(
    *,
    unit_id: str,
    unit_name: str,
    item_name: str,
    description: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "unitId": safe_id(unit_id),
        "unitName": unit_name,
        "unitItemName": item_name,
    }
    if description:
        payload["description"] = description
    KolayClient().post("v2/unit/create-unit-item", data=payload)
    return {"status": "created", "item_name": item_name, "unit_name": unit_name}
