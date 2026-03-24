"""AI Circuit Breaker — per-tenant, per-tool sliding-window rate limiter.

Protects against "Infinite Reasoning Loops": autonomous agents stuck repeatedly
calling the same tool (Denial of Wallet attack).

Design
------
- Keyed by (tenant_id, tool_name) — a tuple of privacy-safe identifiers.
  tenant_id should be rate_limiter.token_key(raw_token), not the raw token.
- Sliding window: O(N_hits) eviction using collections.deque.  For typical
  limits (5 calls/60s) the deque is tiny and eviction is O(1) amortised.
- All state lives in-process memory.  No Redis, no external deps.
- Thread-safe via a single module-level lock (reads are fast, contention rare).

Configuration (env vars, all optional)
---------------------------------------
  MCP_CIRCUIT_BREAKER_ENABLED   – "true"/"1"/"yes" (default: enabled)
  MCP_CB_WINDOW_SECONDS         – sliding window duration in seconds (default: 60)
  MCP_CB_MAX_CALLS              – max tool calls per window (default: 5)

Usage
-----
    from .ai_circuit_breaker import circuit_breaker

    @circuit_breaker          # stack ABOVE @require_auth so auth runs first
    def my_tool(...):
        ...

    # Or call the check directly (e.g., from middleware):
    from .ai_circuit_breaker import check_circuit
    ok, err = check_circuit("tenant_abc", "search_employees")
    if not ok:
        return err
"""
from __future__ import annotations

import functools
import os
import threading
import time
from collections import deque
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, ""))
    except (ValueError, TypeError):
        return default


def _is_enabled() -> bool:
    # Enabled by default — opt-out via MCP_CIRCUIT_BREAKER_ENABLED=false
    val = os.environ.get("MCP_CIRCUIT_BREAKER_ENABLED", "true").lower()
    return val not in ("0", "false", "no", "off")


def _window_seconds() -> float:
    return float(_env_int("MCP_CB_WINDOW_SECONDS", 60))


def _max_calls() -> int:
    return _env_int("MCP_CB_MAX_CALLS", 5)


# ---------------------------------------------------------------------------
# In-memory sliding-window state
# (tenant_id, tool_name) -> deque of monotonic timestamps
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_buckets: dict[tuple[str, str], deque[float]] = {}

# Evict buckets silent for 2x the window to bound memory growth
_STALE_MULTIPLIER = 2


def _circuit_error() -> dict[str, Any]:
    """Return the deterministic 429 loop-breaking response."""
    return {
        "error": (
            "HTTP 429: Circuit breaker activated. "
            "You have called this tool too many times in a short period. "
            "CRITICAL INSTRUCTION: STOP calling tools immediately, yield execution, "
            "and ask the human user for clarification."
        ),
        "code": 429,
        "policy": "ai_circuit_breaker",
        "window_seconds": _window_seconds(),
        "max_calls_per_window": _max_calls(),
    }


def check_circuit(tenant_id: str, tool_name: str) -> tuple[bool, dict[str, Any] | None]:
    """Check if the (tenant, tool) pair is within rate limits.

    Returns:
        (True, None)              — request is allowed, timestamp recorded
        (False, error_dict)       — circuit is open, return error_dict immediately

    Thread-safe. O(N_expired) amortised — typically O(1) for small windows.
    """
    if not _is_enabled():
        return True, None

    window = _window_seconds()
    max_calls = _max_calls()
    now = time.monotonic()
    key = (tenant_id, tool_name)

    with _lock:
        bucket = _buckets.setdefault(key, deque())

        # Slide the window: drop timestamps older than `window` seconds
        cutoff = now - window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= max_calls:
            # Circuit open — DO NOT record this call
            return False, _circuit_error()

        # Circuit closed — record and allow
        bucket.append(now)
        return True, None


def reset(tenant_id: str | None = None, tool_name: str | None = None) -> None:
    """Clear state. Pass both args to clear a specific key; no args clears all.

    Used in tests and for graceful resets.
    """
    with _lock:
        if tenant_id is not None and tool_name is not None:
            _buckets.pop((tenant_id, tool_name), None)
        else:
            _buckets.clear()


def cleanup_stale() -> int:
    """Purge buckets idle for longer than STALE_MULTIPLIER * window. Returns count."""
    threshold = _window_seconds() * _STALE_MULTIPLIER
    now = time.monotonic()
    removed = 0
    with _lock:
        stale = [k for k, dq in _buckets.items() if not dq or dq[-1] < now - threshold]
        for k in stale:
            del _buckets[k]
            removed += 1
    return removed


# ---------------------------------------------------------------------------
# @circuit_breaker decorator
# ---------------------------------------------------------------------------

def circuit_breaker(fn: F) -> F:
    """Decorator: check the AI circuit breaker before executing *fn*.

    Extracts tenant_id from the active request context (KOLAY_TOKEN_CTX).
    Falls back to "anonymous" if no token is present.

    Stack order (outermost first):
        @circuit_breaker    ← checked FIRST, before any heavy computation
        @require_auth       ← auth validated second
        def my_tool(...)
    """
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        from .auth import KOLAY_TOKEN_CTX
        from .rate_limiter import token_key

        raw_token = KOLAY_TOKEN_CTX.get()
        tenant_id = token_key(raw_token) if raw_token else "anonymous"
        tool_name = fn.__name__

        allowed, err = check_circuit(tenant_id, tool_name)
        if not allowed:
            return err

        return fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
