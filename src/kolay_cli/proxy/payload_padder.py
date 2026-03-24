"""Payload Padding Middleware — uniform response sizes against traffic analysis."""
from __future__ import annotations

import json
import os
import secrets
from typing import Any

from kolay_cli.mcp.adapter import TextContent

os.environ.setdefault("FASTMCP_LOG_LEVEL", "WARNING")

from kolay_cli.mcp.adapter import ToolResult, Middleware, MiddlewareContext, CallNext


def _get_pad_target() -> int:
    """Return target response size in bytes (default 64 KB)."""
    kb = int(os.environ.get("MCP_PAD_TARGET_KB", "64"))
    return max(1024, kb * 1024)  # floor at 1 KB


class PayloadPaddingMiddleware(Middleware):
    """FastMCP middleware that pads JSON tool responses to a uniform size.

    This prevents traffic-analysis attacks where an observer can guess
    which API endpoint was called based on encrypted packet sizes.
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: CallNext,
    ) -> ToolResult:
        result = await call_next(context)

        if not result or not result.content:
            return result

        target = _get_pad_target()

        new_contents = []
        for block in result.content:
            if isinstance(block, TextContent):
                current_size = len(block.text.encode("utf-8"))
                if current_size < target:
                    try:
                        data = json.loads(block.text)
                        deficit = target - current_size
                        # Fill with cryptographically random URL-safe noise
                        data["_pad"] = secrets.token_urlsafe(deficit)[:deficit]
                        new_contents.append(
                            TextContent(type="text", text=json.dumps(data, ensure_ascii=False, default=str))
                        )
                    except (json.JSONDecodeError, TypeError):
                        # Non-JSON text — pad with trailing whitespace
                        deficit = target - current_size
                        new_contents.append(
                            TextContent(type="text", text=block.text + " " * deficit)
                        )
                else:
                    new_contents.append(block)
            else:
                new_contents.append(block)

        result.content = new_contents
        return result
