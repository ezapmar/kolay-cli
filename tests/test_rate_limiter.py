"""Tests for the in-memory per-token rate limiter."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from kolay_cli.rate_limiter import (
    check_rate_limit,
    cleanup_stale_entries,
    get_per_hour_limit,
    get_per_minute_limit,
    is_rate_limit_enabled,
    reset,
    token_key,
)


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset rate limiter state before each test."""
    reset()
    yield
    reset()


# ── token_key ────────────────────────────────────────────────────────────────

class TestTokenKey:
    def test_returns_suffix(self):
        assert token_key("abcdefghijklmnop") == "tok_…ijklmnop"

    def test_short_token(self):
        assert token_key("abc") == "tok_…abc"

    def test_empty_token(self):
        assert token_key("") == "tok_…anonymous"


# ── is_rate_limit_enabled ────────────────────────────────────────────────────

class TestConfig:
    @pytest.mark.parametrize("val", ["true", "True", "TRUE", "1", "yes", "YES"])
    def test_enabled_values(self, val):
        with patch.dict(os.environ, {"MCP_RATE_LIMIT_ENABLED": val}):
            assert is_rate_limit_enabled() is True

    @pytest.mark.parametrize("val", ["false", "0", "no", ""])
    def test_disabled_values(self, val):
        with patch.dict(os.environ, {"MCP_RATE_LIMIT_ENABLED": val}):
            assert is_rate_limit_enabled() is False

    def test_not_set(self):
        env = os.environ.copy()
        env.pop("MCP_RATE_LIMIT_ENABLED", None)
        with patch.dict(os.environ, env, clear=True):
            assert is_rate_limit_enabled() is False

    def test_env_var_per_minute(self):
        with patch.dict(os.environ, {"MCP_RATE_LIMIT_PER_MINUTE": "5"}):
            assert get_per_minute_limit() == 5

    def test_env_var_per_hour(self):
        with patch.dict(os.environ, {"MCP_RATE_LIMIT_PER_HOUR": "100"}):
            assert get_per_hour_limit() == 100

    def test_env_var_invalid_falls_back(self):
        with patch.dict(os.environ, {"MCP_RATE_LIMIT_PER_MINUTE": "abc"}):
            assert get_per_minute_limit() == 30  # default


# ── check_rate_limit ─────────────────────────────────────────────────────────

class TestCheckRateLimit:
    def test_under_limit_passes(self):
        with patch.dict(os.environ, {"MCP_RATE_LIMIT_PER_MINUTE": "5"}):
            for i in range(5):
                allowed, detail = check_rate_limit("tok_…test1234")
                assert allowed is True, f"Call {i+1} should be allowed"
                assert "remaining_minute" in detail

    def test_over_per_minute_limit_blocked(self):
        with patch.dict(os.environ, {"MCP_RATE_LIMIT_PER_MINUTE": "3"}):
            for _ in range(3):
                allowed, _ = check_rate_limit("tok_…test1234")
                assert allowed is True

            # 4th call should be blocked
            allowed, detail = check_rate_limit("tok_…test1234")
            assert allowed is False
            assert detail["remaining_minute"] == 0
            assert "retry_after_seconds" in detail
            assert detail["retry_after_seconds"] > 0

    def test_different_keys_independent(self):
        with patch.dict(os.environ, {"MCP_RATE_LIMIT_PER_MINUTE": "2"}):
            # Exhaust key A
            check_rate_limit("tok_…aaaaaaaa")
            check_rate_limit("tok_…aaaaaaaa")
            allowed_a, _ = check_rate_limit("tok_…aaaaaaaa")
            assert allowed_a is False

            # Key B should still be fine
            allowed_b, _ = check_rate_limit("tok_…bbbbbbbb")
            assert allowed_b is True

    def test_remaining_counts_decrement(self):
        with patch.dict(os.environ, {"MCP_RATE_LIMIT_PER_MINUTE": "10", "MCP_RATE_LIMIT_PER_HOUR": "100"}):
            _, d1 = check_rate_limit("tok_…test1234")
            _, d2 = check_rate_limit("tok_…test1234")
            assert d2["remaining_minute"] == d1["remaining_minute"] - 1
            assert d2["remaining_hour"] == d1["remaining_hour"] - 1


# ── cleanup_stale_entries ────────────────────────────────────────────────────

class TestCleanup:
    def test_cleanup_removes_stale(self):
        # Add an entry
        check_rate_limit("tok_…stale123")

        # Manually make it stale by clearing the deque
        from kolay_cli.rate_limiter import _buckets, _lock
        with _lock:
            _buckets["tok_…stale123"].clear()

        removed = cleanup_stale_entries()
        assert removed == 1

    def test_cleanup_keeps_active(self):
        check_rate_limit("tok_…active12")
        removed = cleanup_stale_entries()
        assert removed == 0
