"""FastMCP adapter — sole contact surface with the fastmcp package.

ALL fastmcp imports in this project MUST go through this file.
When upgrading fastmcp, only fix this file, then run tests.

Usage from any tools_*.py or mcp_server.py:
    from .adapter import Tool, Context, CurrentContext, FastMCP
    from .adapter import (
        ErrorHandlingMiddleware,
        SlidingWindowRateLimitingMiddleware,
        TimingMiddleware,
        ResponseLimitingMiddleware,
        PingMiddleware,
    )

FastMCP version pinned in pyproject.toml [project.dependencies].
"""
from __future__ import annotations

# ── Core ──────────────────────────────────────────────────────────────────────
from fastmcp import FastMCP  # noqa: F401

# ── Tools ─────────────────────────────────────────────────────────────────────
from fastmcp.tools import Tool  # noqa: F401

# ── Context ───────────────────────────────────────────────────────────────────
from fastmcp.server.context import Context  # noqa: F401
from fastmcp.dependencies import CurrentContext  # noqa: F401

# ── Middleware ─────────────────────────────────────────────────────────────────
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware  # noqa: F401
from fastmcp.server.middleware.rate_limiting import SlidingWindowRateLimitingMiddleware  # noqa: F401
from fastmcp.server.middleware.timing import TimingMiddleware  # noqa: F401
from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware  # noqa: F401
from fastmcp.server.middleware import PingMiddleware  # noqa: F401

# ── Internal tool types (used by pii_masker / payload_padder) ─────────────────
try:
    from fastmcp.tools.tool import ToolResult  # noqa: F401
    from fastmcp.server.middleware.middleware import (  # noqa: F401
        Middleware,
        MiddlewareContext,
        CallNext,
    )
except ImportError:
    # fastmcp version without these symbols — provide stubs
    from typing import Any
    ToolResult = None  # type: ignore[assignment,misc]
    Middleware = object  # type: ignore[assignment,misc]
    MiddlewareContext = Any  # type: ignore[assignment,misc]
    CallNext = Any  # type: ignore[assignment,misc]

# ── Progress / context helpers ─────────────────────────────────────────────────
try:
    from mcp.types import TextContent  # noqa: F401
except ImportError:
    TextContent = None  # type: ignore[assignment,misc]
