"""Session state tools — LLM-controlled per-session key-value memory.

These tools let an LLM persist and retrieve named values across tool calls
within the same MCP session (e.g. remember a person_id, department name,
or working date range without repeating them on every call).

State is in-memory and session-scoped: cleared automatically when the
session ends. No PII is written to disk.
"""
from __future__ import annotations

from typing import Any
from fastmcp.server.context import Context
from fastmcp.tools import Tool


async def session_remember(key: str, value: str, ctx: Context) -> dict[str, Any]:
    """[READ] Store a named value in session memory.
    Use this to remember things across tool calls within the same conversation:
    e.g. a person_id, department name, or date range you'll need repeatedly.
    key: short name (e.g. 'focus_person', 'department', 'review_start').
    value: the value to store (stored as a string)."""
    await ctx.set_state(key, value)
    return {"stored": True, "key": key, "value": value}


async def session_recall(key: str, ctx: Context) -> dict[str, Any]:
    """[READ] Retrieve a named value previously stored with session_remember.
    Returns the value if found, or null if the key has not been set.
    key: the name used when calling session_remember."""
    value = await ctx.get_state(key)
    if value is None:
        return {"found": False, "key": key, "value": None}
    return {"found": True, "key": key, "value": value}


async def session_forget(key: str, ctx: Context) -> dict[str, Any]:
    """[READ] Remove a named value from session memory.
    key: the name to delete."""
    await ctx.delete_state(key)
    return {"deleted": True, "key": key}


def register(mcp) -> None:
    mcp.add_tool(Tool.from_function(session_remember,
        tags={"read", "session"},
        annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    ))
    mcp.add_tool(Tool.from_function(session_recall,
        tags={"read", "session"},
        annotations={"readOnlyHint": True, "openWorldHint": False},
    ))
    mcp.add_tool(Tool.from_function(session_forget,
        tags={"session"},
        annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    ))
