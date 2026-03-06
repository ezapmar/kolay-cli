"""Expense services."""
from __future__ import annotations

from typing import Any

from ..api.client import KolayClient


def list_categories(
    *,
    title: str | None = None,
    enabled_only: bool = False,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {}
    if title:
        params["title"] = title
    if enabled_only:
        params["isEnable"] = 1
    return KolayClient().get("v2/expense/list-categories", params=params).get("data", [])
