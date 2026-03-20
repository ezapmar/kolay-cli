"""Shared async-to-sync progress bridge for MCP tools."""
from __future__ import annotations

import asyncio
from typing import Callable
from fastmcp.server.context import Context


def sync_progress_bridge(ctx: Context) -> Callable[[int, int, str], None]:
    """Return a synchronous callback that sends progress back to the MCP context."""

    async def _progress(step: int, total: int, msg: str) -> None:
        await ctx.report_progress(progress=step, total=total)
        await ctx.info(msg)

    def _sync_progress(step: int, total: int, msg: str) -> None:
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(_progress(step, total, msg))
        except RuntimeError:
            pass  # If there is no active loop, we gracefully drop progress updates

    return _sync_progress
