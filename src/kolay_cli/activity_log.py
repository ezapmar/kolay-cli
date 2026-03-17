"""Structured activity logger for MCP tool calls.

Outputs one JSON object per tool invocation to stdout via Python logging.
Railway (and most container runtimes) automatically capture stdout.

Privacy rules:
  - Token is logged only as a last-8-char suffix key (``tok_…abcd1234``).
  - Response payloads are **never** logged.
  - Argument values longer than 64 characters are redacted.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger("kolay.activity")

# Ensure we have at least one handler writing to stdout
if not _logger.handlers:
    import sys
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False

_REDACT_THRESHOLD = 64


def _redact_args(args: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *args* with long string values redacted."""
    redacted: dict[str, Any] = {}
    for k, v in args.items():
        if isinstance(v, str) and len(v) > _REDACT_THRESHOLD:
            redacted[k] = f"[redacted:{len(v)} chars]"
        elif isinstance(v, dict):
            redacted[k] = _redact_args(v)
        else:
            redacted[k] = v
    return redacted


def log_tool_call(
    token_key: str,
    tool_name: str,
    args: dict[str, Any],
    duration_s: float,
    *,
    success: bool = True,
    error: str | None = None,
) -> None:
    """Emit a single structured JSON log line for a tool invocation.

    Args:
        token_key:  Privacy-safe token identifier (e.g. ``tok_…a1b2c3d4``).
        tool_name:  Name of the MCP tool function.
        args:       Keyword arguments passed to the tool (will be redacted).
        duration_s: Wall-clock duration in seconds (monotonic).
        success:    Whether the call completed without exception.
        error:      Error message string if ``success`` is False.
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "mcp.tool_call",
        "token_key": token_key,
        "tool": tool_name,
        "args_summary": _redact_args(args) if args else {},
        "duration_ms": round(duration_s * 1000, 1),
        "success": success,
        "error": error,
    }
    _logger.info(json.dumps(record, ensure_ascii=False, default=str))
