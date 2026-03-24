"""Tests for the k-anonymity guardrail in tools_smart_proxy."""
from __future__ import annotations

import pytest

from kolay_cli.mcp.tools_smart_proxy import (
    MIN_COHORT_SIZE,
    _check_k_anonymity,
    _k_anonymity_error,
)


class TestKAnonymityConstants:
    def test_min_cohort_size_is_three(self) -> None:
        assert MIN_COHORT_SIZE == 3


class TestKAnonymityError:
    def test_error_message_contains_http_451(self) -> None:
        err = _k_anonymity_error(1, {})
        assert "HTTP 451" in err["error"]

    def test_error_message_reflects_cohort_size(self) -> None:
        err = _k_anonymity_error(2, {"department": "Engineering"})
        assert "2 employees" in err["error"]

    def test_singular_employee_grammar(self) -> None:
        err = _k_anonymity_error(1, {})
        assert "1 employee" in err["error"]
        assert "1 employees" not in err["error"]

    def test_error_contains_min_cohort_size(self) -> None:
        err = _k_anonymity_error(2, {})
        assert err["min_cohort_size"] == MIN_COHORT_SIZE

    def test_error_contains_filters_applied(self) -> None:
        filters = {"department": "HR", "other": "value"}
        err = _k_anonymity_error(1, filters)
        assert err["filters_applied"] == filters

    def test_error_contains_privacy_policy_label(self) -> None:
        err = _k_anonymity_error(1, {})
        assert err["privacy_policy"] == "k-anonymity"

    def test_error_key_is_present(self) -> None:
        err = _k_anonymity_error(1, {})
        assert "error" in err

    def test_never_raises(self) -> None:
        # Must not raise for any reasonable input
        for n in range(0, MIN_COHORT_SIZE):
            result = _k_anonymity_error(n, {})
            assert isinstance(result, dict)


class TestCheckKAnonymity:
    """_check_k_anonymity returns None (pass) or an error dict (block)."""

    def _make_pool(self, size: int) -> list[dict]:
        return [{"id": str(i)} for i in range(size)]

    # -- Block cases --

    def test_single_employee_is_blocked(self) -> None:
        result = _check_k_anonymity(self._make_pool(1), {})
        assert result is not None
        assert "HTTP 451" in result["error"]

    def test_two_employees_are_blocked(self) -> None:
        result = _check_k_anonymity(self._make_pool(2), {})
        assert result is not None

    # -- Pass cases --

    def test_exactly_min_cohort_is_allowed(self) -> None:
        assert _check_k_anonymity(self._make_pool(MIN_COHORT_SIZE), {}) is None

    def test_large_pool_is_allowed(self) -> None:
        assert _check_k_anonymity(self._make_pool(1000), {}) is None

    # -- Edge cases --

    def test_empty_pool_is_not_blocked(self) -> None:
        # Empty pools are handled later by the caller ("no matching employees")
        assert _check_k_anonymity([], {}) is None

    def test_blocked_result_contains_correct_cohort_size(self) -> None:
        result = _check_k_anonymity(self._make_pool(1), {"department": "Legal"})
        assert result is not None
        assert result["cohort_size"] == 1

    def test_filters_passed_through_to_error(self) -> None:
        filters = {"department": "Finance", "metric": "headcount"}
        result = _check_k_anonymity(self._make_pool(2), filters)
        assert result is not None
        assert result["filters_applied"] == filters


class TestGetEmployeeStatisticsKAnonymity:
    """Integration test: get_employee_statistics must honour k-anonymity."""

    def _single_employee_pool(self) -> list[dict]:
        return [{
            "id": "x1",
            "firstName": "Ayse",
            "lastName": "Yilmaz",
            "department": "UniqueDept",
            "birthDate": "1991-06-01",
            "employmentStartDate": "2022-01-01",
            "status": "active",
            "title": "Engineer",
        }]

    def test_cohort_too_small_returns_451_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import kolay_cli.mcp.tools_smart_proxy as proxy

        # Patch fetch_all_employees to return exactly 1 record
        monkeypatch.setattr(proxy, "fetch_all_employees", lambda: self._single_employee_pool())

        # Bypass auth decorator by calling the underlying function directly
        from kolay_cli.mcp.tools_smart_proxy import get_employee_statistics
        inner = get_employee_statistics.__wrapped__ if hasattr(get_employee_statistics, "__wrapped__") else None

        # Call via require_auth — patch token resolution to succeed
        import kolay_cli.security as sec
        monkeypatch.setattr(sec, "resolve_token", lambda: "fake-opaque-token")

        result = get_employee_statistics(metric="headcount")
        assert "HTTP 451" in result.get("error", ""), (
            f"Expected 451 block, got: {result}"
        )

    def test_sufficient_cohort_returns_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import kolay_cli.mcp.tools_smart_proxy as proxy
        import kolay_cli.security as sec

        pool = [
            {
                "id": f"id{i}", "firstName": "A", "lastName": "B",
                "department": "Engineering", "birthDate": "1990-01-01",
                "employmentStartDate": "2020-01-01", "status": "active", "title": "Eng",
            }
            for i in range(10)
        ]

        monkeypatch.setattr(proxy, "fetch_all_employees", lambda: pool)
        monkeypatch.setattr(sec, "resolve_token", lambda: "fake-opaque-token")

        from kolay_cli.mcp.tools_smart_proxy import get_employee_statistics
        result = get_employee_statistics(metric="headcount")
        # Should not be blocked
        assert "HTTP 451" not in result.get("error", ""), result
        assert result.get("value") == 10
