"""
Kolay IK services — pure business logic layer.

Each module exposes plain functions that call KolayClient and return
raw dicts/lists.  No Rich formatting, no Typer, no CLI concerns.

Used by both CLI commands (commands/) and MCP tools (mcp_server.py).
"""
from __future__ import annotations

from . import person, leave, timelog, training, transaction, calendar, unit, approval, expense, nudge

__all__ = [
    "person", "leave", "timelog", "training", "transaction",
    "calendar", "unit", "approval", "expense", "nudge"
]
