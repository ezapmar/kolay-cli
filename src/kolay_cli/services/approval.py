"""Approval process services."""
from __future__ import annotations

from typing import Any

from ..api.client import KolayClient


def list_approval_processes() -> list[dict[str, Any]]:
    raw = KolayClient().get("v2/approval-process/list").get("data", [])
    if isinstance(raw, dict):
        items = raw.get("items", [])
    elif isinstance(raw, list):
        items = raw
    else:
        items = []
    return [ap for ap in items if isinstance(ap, dict)]
