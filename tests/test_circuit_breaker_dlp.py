"""Tests for:
  - AI Circuit Breaker  (ai_circuit_breaker.py)
  - Egress DLP Scanner  (egress_dlp.py)
"""
from __future__ import annotations

import time

import pytest

from kolay_cli.ai_circuit_breaker import (
    check_circuit,
    reset as cb_reset,
    cleanup_stale,
    _circuit_error,
    _max_calls,
    _window_seconds,
)
from kolay_cli.egress_dlp import (
    scan_string,
    scan_and_redact,
    _REDACTION_TOKEN,
    _PATTERNS,
)


# ===========================================================================
# AI Circuit Breaker
# ===========================================================================

class TestCircuitBreakerCheckCircuit:

    def setup_method(self) -> None:
        cb_reset()

    def test_first_calls_are_allowed(self) -> None:
        for _ in range(_max_calls()):
            allowed, err = check_circuit("tenant_a", "search_employees")
            assert allowed is True
            assert err is None

    def test_exceeding_limit_is_blocked(self) -> None:
        for _ in range(_max_calls()):
            check_circuit("tenant_a", "search_employees")
        allowed, err = check_circuit("tenant_a", "search_employees")
        assert allowed is False
        assert err is not None

    def test_blocked_response_contains_http_429(self) -> None:
        for _ in range(_max_calls()):
            check_circuit("t1", "tool_x")
        _, err = check_circuit("t1", "tool_x")
        assert err is not None
        assert "HTTP 429" in err["error"]

    def test_blocked_response_contains_stop_instruction(self) -> None:
        for _ in range(_max_calls()):
            check_circuit("t1", "tool_x")
        _, err = check_circuit("t1", "tool_x")
        assert "STOP calling tools immediately" in err["error"]

    def test_blocked_response_contains_policy_field(self) -> None:
        for _ in range(_max_calls()):
            check_circuit("t1", "tool_x")
        _, err = check_circuit("t1", "tool_x")
        assert err["policy"] == "ai_circuit_breaker"
        assert err["code"] == 429

    def test_different_tools_have_independent_buckets(self) -> None:
        for _ in range(_max_calls()):
            check_circuit("t1", "tool_a")
        # tool_b should still be allowed
        allowed, _ = check_circuit("t1", "tool_b")
        assert allowed is True

    def test_different_tenants_are_independent(self) -> None:
        for _ in range(_max_calls()):
            check_circuit("tenant_a", "search_employees")
        # tenant_b's circuit is unaffected
        allowed, _ = check_circuit("tenant_b", "search_employees")
        assert allowed is True

    def test_window_resets_after_expiry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Demonstrate sliding-window expiry: old hits drop out."""
        import kolay_cli.ai_circuit_breaker as cb_mod

        fake_time = [0.0]
        monkeypatch.setattr(cb_mod.time, "monotonic", lambda: fake_time[0])
        cb_reset()

        window = _window_seconds()

        # Fill up the window
        for _ in range(_max_calls()):
            check_circuit("t1", "tool_x")

        # Still blocked at t=0
        allowed, _ = check_circuit("t1", "tool_x")
        assert allowed is False

        # Advance time past the window
        fake_time[0] = window + 1.0

        # Old timestamps evicted — circuit is open again
        allowed, _ = check_circuit("t1", "tool_x")
        assert allowed is True

    def test_disabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MCP_CIRCUIT_BREAKER_ENABLED", "false")
        # Exceed the normal limit — should still allow
        for _ in range(_max_calls() + 10):
            allowed, err = check_circuit("t1", "tool_x")
            assert allowed is True

    def test_reset_specific_key(self) -> None:
        for _ in range(_max_calls()):
            check_circuit("t1", "tool_x")
        cb_reset("t1", "tool_x")
        allowed, _ = check_circuit("t1", "tool_x")
        assert allowed is True

    def test_cleanup_stale_removes_old_buckets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import kolay_cli.ai_circuit_breaker as cb_mod
        fake_time = [0.0]
        monkeypatch.setattr(cb_mod.time, "monotonic", lambda: fake_time[0])
        cb_reset()

        check_circuit("stale_t", "stale_tool")  # records at t=0
        fake_time[0] = _window_seconds() * 3    # well past stale threshold
        removed = cleanup_stale()
        assert removed >= 1


class TestCircuitErrorShape:
    def test_error_has_all_required_fields(self) -> None:
        err = _circuit_error()
        assert "error" in err
        assert "code" in err
        assert err["code"] == 429
        assert "policy" in err
        assert "window_seconds" in err
        assert "max_calls_per_window" in err


# ===========================================================================
# Egress DLP Scanner
# ===========================================================================

class TestScanString:

    def test_tc_kimlik_is_redacted(self) -> None:
        text = '{"national_id": "12345678901"}'
        result, count = scan_string(text)
        assert _REDACTION_TOKEN in result
        assert "12345678901" not in result
        assert count == 1

    def test_tc_kimlik_starting_with_zero_not_matched(self) -> None:
        # TC Kimlik cannot start with 0
        text = '{"id": "01234567890"}'
        result, count = scan_string(text)
        assert count == 0

    def test_turkish_iban_is_redacted(self) -> None:
        text = '{"iban": "TR330006100519786457841326"}'
        result, count = scan_string(text)
        assert _REDACTION_TOKEN in result
        assert "TR330006100519786457841326" not in result
        assert count >= 1

    def test_generic_iban_is_redacted(self) -> None:
        text = '{"bank": "DE89370400440532013000"}'
        result, count = scan_string(text)
        assert _REDACTION_TOKEN in result
        assert count >= 1

    def test_clean_payload_has_zero_matches(self) -> None:
        text = '{"firstName": "Ayse", "department": "Engineering", "status": "active"}'
        _, count = scan_string(text)
        assert count == 0

    def test_multiple_pii_in_single_payload(self) -> None:
        text = (
            '{"national_id": "12345678901", '
            '"iban": "TR330006100519786457841326", '
            '"name": "Ali"}'
        )
        result, count = scan_string(text)
        assert count >= 2
        assert "12345678901" not in result
        assert "TR330006100519786457841326" not in result
        assert "Ali" in result  # safe field untouched

    def test_redaction_token_is_correct_string(self) -> None:
        text = '{"ssn": "12345678901"}'
        result, _ = scan_string(text)
        assert "[REDACTED_BY_KOLAYIK_DLP]" in result

    def test_empty_string(self) -> None:
        result, count = scan_string("")
        assert result == ""
        assert count == 0


class TestScanAndRedact:

    def test_dict_with_pii_is_redacted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KOLAY_SECURITY_PROFILE", "enterprise")
        data = {"national_id": "12345678901", "name": "Ayse"}
        result = scan_and_redact(data)
        assert isinstance(result, dict)
        assert result["national_id"] == _REDACTION_TOKEN
        assert result["name"] == "Ayse"

    def test_clean_dict_returned_as_same_object(self) -> None:
        data = {"firstName": "Ali", "department": "Engineering"}
        result = scan_and_redact(data)
        # No PII: same semantic content, fast path
        assert result == data

    def test_nested_pii_in_list_is_redacted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KOLAY_SECURITY_PROFILE", "enterprise")
        data = [{"id": "1", "iban": "TR330006100519786457841326"}]
        result = scan_and_redact(data)
        assert isinstance(result, list)
        assert result[0]["iban"] == _REDACTION_TOKEN

    def test_disabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MCP_DLP_ENABLED", "false")
        data = {"national_id": "12345678901"}
        result = scan_and_redact(data)
        # DLP disabled — orignal value passes through
        assert result == data

    def test_non_pii_numbers_not_redacted(self) -> None:
        # 10-digit number is NOT a TC Kimlik (11 digits required)
        data = {"employee_count": 1234567890}
        result = scan_and_redact(data)
        assert result == data

    def test_performance_large_payload(self) -> None:
        """DLP scan on a 3000-employee clean payload must complete in < 100 ms."""
        employees = [
            {
                "id": f"emp{i:04d}",
                "firstName": "Ali",
                "lastName": "Yilmaz",
                "department": "Engineering",
                "status": "active",
            }
            for i in range(3000)
        ]
        t0 = time.monotonic()
        result = scan_and_redact(employees)
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert len(result) == 3000
        assert elapsed_ms < 100, f"DLP scan took {elapsed_ms:.1f} ms (> 100 ms budget)"

    def test_pii_in_error_payload_is_redacted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DLP must also scan error payloads — PII can leak in error messages."""
        monkeypatch.setenv("KOLAY_SECURITY_PROFILE", "enterprise")
        data = {
            "error": True,
            "message": "Employee 12345678901 not found",
        }
        result = scan_and_redact(data)
        assert "12345678901" not in result["message"]
        assert _REDACTION_TOKEN in result["message"]
