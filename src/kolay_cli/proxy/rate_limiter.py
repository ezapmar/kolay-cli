"""In-memory per-token rate limiter for the MCP proxy.

Sliding-window algorithm using collections.deque with timestamps.
Keyed by a privacy-safe token suffix (last 8 chars).

Environment variables:
  MCP_RATE_LIMIT_ENABLED       – "true"/"1"/"yes" to activate (default: off)
  MCP_RATE_LIMIT_PER_MINUTE    – max tool calls per minute per token (default: 30)
  MCP_RATE_LIMIT_PER_HOUR      – max tool calls per hour per token (default: 500)
"""
from __future__ import annotations

import os
import time
import threading
from collections import deque
from typing import Any


# ── Configuration ─────────────────────────────────────────────────────────────

def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key, "")
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


def is_rate_limit_enabled() -> bool:
    return os.environ.get("MCP_RATE_LIMIT_ENABLED", "").lower() in ("1", "true", "yes")


def get_per_minute_limit() -> int:
    return _env_int("MCP_RATE_LIMIT_PER_MINUTE", 30)


def get_per_hour_limit() -> int:
    return _env_int("MCP_RATE_LIMIT_PER_HOUR", 500)


# ── Token key ─────────────────────────────────────────────────────────────────

def token_key(raw_token: str) -> str:
    """Return a privacy-safe key derived from the last 8 characters of the token.

    Example: "eyJhbGciOiJIUzI1NiIsIn..." → "tok_…iIsIn..."
    """
    if not raw_token:
        return "tok_…anonymous"
    suffix = raw_token[-8:] if len(raw_token) >= 8 else raw_token
    return f"tok_…{suffix}"


# ── Sliding-window state ─────────────────────────────────────────────────────

_lock = threading.Lock()

# token_key → deque of timestamps (monotonic seconds)
_buckets: dict[str, deque[float]] = {}

_MINUTE = 60.0
_HOUR = 3600.0
_STALE_THRESHOLD = 2 * _HOUR  # purge entries not seen in 2 hours


def check_rate_limit(key: str) -> tuple[bool, dict[str, Any]]:
    """Check whether a request from *key* is allowed.

    Returns:
        (allowed, detail) where detail contains remaining counts and,
        if blocked, a ``retry_after_seconds`` value.
    """
    now = time.monotonic()
    per_min = get_per_minute_limit()
    per_hr = get_per_hour_limit()

    with _lock:
        bucket = _buckets.setdefault(key, deque())

        # Expire entries older than 1 hour
        while bucket and bucket[0] < now - _HOUR:
            bucket.popleft()

        # Count hits in the last minute / hour
        minute_cutoff = now - _MINUTE
        hits_minute = sum(1 for ts in bucket if ts >= minute_cutoff)
        hits_hour = len(bucket)

        # Determine if blocked
        if hits_minute >= per_min:
            # Find the oldest timestamp in the current minute window to
            # compute when it will expire.
            oldest_in_window = next(ts for ts in bucket if ts >= minute_cutoff)
            retry_after = round(oldest_in_window + _MINUTE - now, 1)
            return False, {
                "retry_after_seconds": max(retry_after, 0.1),
                "limit": f"{per_min}/min",
                "remaining_minute": 0,
                "remaining_hour": max(per_hr - hits_hour, 0),
            }

        if hits_hour >= per_hr:
            oldest_in_window = bucket[0]
            retry_after = round(oldest_in_window + _HOUR - now, 1)
            return False, {
                "retry_after_seconds": max(retry_after, 0.1),
                "limit": f"{per_hr}/hour",
                "remaining_minute": max(per_min - hits_minute, 0),
                "remaining_hour": 0,
            }

        # Allowed — record the hit
        bucket.append(now)

        return True, {
            "remaining_minute": per_min - hits_minute - 1,
            "remaining_hour": per_hr - hits_hour - 1,
        }


def cleanup_stale_entries() -> int:
    """Remove buckets for tokens not seen in the last 2 hours.

    Returns the number of entries removed.
    """
    now = time.monotonic()
    removed = 0
    with _lock:
        stale_keys = [
            k for k, dq in _buckets.items()
            if not dq or dq[-1] < now - _STALE_THRESHOLD
        ]
        for k in stale_keys:
            del _buckets[k]
            removed += 1
    return removed


def reset() -> None:
    """Clear all state. Useful for testing."""
    with _lock:
        _buckets.clear()
