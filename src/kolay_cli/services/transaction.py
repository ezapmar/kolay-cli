"""Transaction services."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ..api.client import KolayClient, safe_id

TRANSACTION_TYPES = [
    "expense", "advancePayment", "bonus", "premium", "otherCut",
    "militaryBenefit", "nationalHolidayBenefit", "fuelAllowanceBenefit",
]


def list_transactions(
    *,
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
        "startDate": f"{year}-01-01 00:00:00",
        "endDate": f"{year}-12-31 23:59:59",
    }
    if person_id:
        payload["personId"] = person_id
    if type:
        payload["type"] = type
    if status:
        payload["status"] = status
    resp = KolayClient().post("v2/transaction/list", data=payload)
    data = resp.get("data", {})
    items = data.get("items", []) if isinstance(data, dict) else []
    total = data.get("totalCount", 0) if isinstance(data, dict) else len(items)
    return {"items": items, "totalCount": total, "page": page}


def view_transaction(transaction_id: str) -> dict[str, Any]:
    return KolayClient().get(f"v2/transaction/view/{safe_id(transaction_id)}").get("data", {})


def create_transaction(
    *,
    person_id: str,
    type: str,
    amount: float,
    date: str,
    currency: str = "TL",
    description: str = "",
) -> dict[str, Any]:
    KolayClient().post("v2/transaction/create", data={
        "personId": safe_id(person_id),
        "type": type, "amount": amount,
        "currency": currency, "date": date,
        "description": description,
    })
    return {"status": "created", "person_id": person_id, "type": type, "amount": amount}


def delete_transaction(transaction_id: str) -> dict[str, Any]:
    KolayClient().delete(f"v2/transaction/delete/{safe_id(transaction_id)}")
    return {"status": "deleted", "id": transaction_id}
