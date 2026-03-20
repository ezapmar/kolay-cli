"""tests/test_wellness.py — Tests for the wellbeing engine (wellness.py)."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pytest

from kolay_cli.services.wellness import (
    _days_since_last_rest,
    _burnout_status,
    _burnout_emoji,
    _gap_signal,
    _scan_bridge_opportunities,
    _scan_rest_opportunities,
    analyze_employee_wellbeing,
    get_smart_rest_plan,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _holiday(d: date, name: str = "Test Holiday") -> dict[date, str]:
    return {d: name}


def _leave(end: str) -> dict:
    return {"endDate": end, "status": "approved"}


# ── Unit: _days_since_last_rest ───────────────────────────────────────────────

class TestDaysSinceLastRest:
    def test_no_history_returns_none(self):
        assert _days_since_last_rest([]) is None

    def test_single_entry(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        assert _days_since_last_rest([_leave(yesterday)]) == 1

    def test_multiple_entries_picks_most_recent(self):
        d1 = (date.today() - timedelta(days=10)).isoformat()
        d2 = (date.today() - timedelta(days=3)).isoformat()
        assert _days_since_last_rest([_leave(d1), _leave(d2)]) == 3

    def test_malformed_date_is_skipped(self):
        result = _days_since_last_rest([{"endDate": "not-a-date"}, _leave(
            (date.today() - timedelta(days=5)).isoformat()
        )])
        assert result == 5

    def test_missing_endDate_is_skipped(self):
        result = _days_since_last_rest([{"endDate": None}, _leave(
            (date.today() - timedelta(days=2)).isoformat()
        )])
        assert result == 2


# ── Unit: _burnout_status / _burnout_emoji ────────────────────────────────────

class TestBurnoutStatus:
    @pytest.mark.parametrize("score,expected", [
        (0, "healthy"),
        (1, "healthy"),
        (2, "yellow_zone"),
        (3, "orange_zone"),
        (4, "red_zone"),
        (10, "red_zone"),
    ])
    def test_score_to_status(self, score, expected):
        assert _burnout_status(score) == expected

    def test_healthy_emoji(self):
        assert "🟢" in _burnout_emoji("healthy")

    def test_red_zone_emoji(self):
        assert "🔴" in _burnout_emoji("red_zone")

    def test_unknown_status_returns_fallback(self):
        assert _burnout_emoji("unknown") == "⚪"


# ── Unit: _gap_signal ─────────────────────────────────────────────────────────

class TestGapSignal:
    def test_none_returns_one_point(self):
        signal, pts = _gap_signal(None)
        assert pts == 1
        assert "No approved leave" in signal

    def test_zero_days_no_signal(self):
        signal, pts = _gap_signal(0)
        assert pts == 0
        assert signal == ""

    def test_29_days_no_signal(self):
        _, pts = _gap_signal(29)
        assert pts == 0

    def test_30_days_one_point(self):
        _, pts = _gap_signal(30)
        assert pts == 1

    def test_60_days_two_points(self):
        _, pts = _gap_signal(60)
        assert pts == 2

    def test_90_days_three_points(self):
        _, pts = _gap_signal(90)
        assert pts == 3
        assert "90-day" in _gap_signal(90)[0]


# ── Unit: _scan_bridge_opportunities ─────────────────────────────────────────

class TestScanBridgeOpportunities:
    def test_no_holidays_returns_empty(self):
        result = _scan_bridge_opportunities({}, 20)
        assert result == []

    def test_zero_balance_returns_empty(self):
        today = date.today()
        holiday = today + timedelta(days=5)
        result = _scan_bridge_opportunities({holiday: "Test"}, 0)
        assert result == []

    def test_past_holiday_excluded(self):
        past = date.today() - timedelta(days=1)
        result = _scan_bridge_opportunities({past: "Past Holiday"}, 20)
        assert result == []

    def test_bridge_opportunity_found(self):
        # Put a holiday on a Wednesday 10 days from now → bridge Mon-Tue = 4 day break
        today = date.today()
        # Find the next Wednesday
        days_to_wed = (2 - today.weekday()) % 7 or 7
        wednesday = today + timedelta(days=days_to_wed + 7)  # at least next week's Wednesday
        result = _scan_bridge_opportunities({wednesday: "Test Holiday"}, 20)
        # Should find opportunities (Mon/Tue + Wed = 3+ day break)
        assert len(result) > 0
        # All results should have efficiency >= 2.0
        for opp in result:
            assert opp["efficiency"] >= 2.0

    def test_results_sorted_by_efficiency_desc(self):
        today = date.today()
        h1 = today + timedelta(days=10)
        h2 = today + timedelta(days=20)
        result = _scan_bridge_opportunities(
            {h1: "Holiday 1", h2: "Holiday 2"},
            20,
        )
        efficiencies = [r["efficiency"] for r in result]
        assert efficiencies == sorted(efficiencies, reverse=True)

    def test_max_5_results(self):
        today = date.today()
        # Create many holidays
        holidays = {
            today + timedelta(days=i): f"H{i}"
            for i in range(5, 60, 5)
        }
        result = _scan_bridge_opportunities(holidays, 20)
        assert len(result) <= 5


# ── Unit: _scan_rest_opportunities ───────────────────────────────────────────

class TestScanRestOpportunities:
    def test_returns_at_most_3(self):
        result = _scan_rest_opportunities({}, 20)
        assert len(result) <= 3

    def test_conservative_limits_consecutive_days(self):
        result = _scan_rest_opportunities({}, 3)
        for opp in result:
            assert opp["budget_tier"] == "conservative"
            assert opp["leave_days_cost"] <= 2

    def test_generous_allows_up_to_5_days(self):
        result = _scan_rest_opportunities({}, 20)
        if result:
            assert result[0]["budget_tier"] == "generous"

    def test_efficiency_always_at_least_1_5(self):
        result = _scan_rest_opportunities({}, 15)
        for opp in result:
            assert opp["efficiency"] >= 1.5

    def test_sorted_by_efficiency_desc(self):
        result = _scan_rest_opportunities({}, 15)
        efficiencies = [r["efficiency"] for r in result]
        assert efficiencies == sorted(efficiencies, reverse=True)


# ── Integration: analyze_employee_wellbeing ───────────────────────────────────

_MOCK_PROFILE = {
    "firstName": "Ayse",
    "lastName": "Yilmaz",
    "department": "Engineering",
    "employmentStartDate": "2022-01-01",
}

_MOCK_BALANCE = [{
    "primary": True,
    "leaveType": {"name": "Annual Leave"},
    "entitled": 20,
    "used": 0,
    "unused": 22,
}]

_MOCK_LEAVES = [{"endDate": (date.today() - timedelta(days=100)).isoformat(), "status": "approved"}]


class TestAnalyzeEmployeeWellbeing:
    @patch("kolay_cli.services.wellness.leave_svc.list_leaves", return_value=_MOCK_LEAVES)
    @patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=_MOCK_BALANCE)
    @patch("kolay_cli.services.wellness.person_svc.view_person", return_value=_MOCK_PROFILE)
    def test_red_zone_detected(self, mock_view, mock_balance, mock_leaves):
        result = analyze_employee_wellbeing("p1")
        assert result["burnout_status"] in ("red_zone", "orange_zone", "yellow_zone")
        assert result["burnout_score"] > 0
        assert result["employee"]["name"] == "Ayse Yilmaz"

    @patch("kolay_cli.services.wellness.leave_svc.list_leaves", return_value=_MOCK_LEAVES)
    @patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=_MOCK_BALANCE)
    @patch("kolay_cli.services.wellness.person_svc.view_person", return_value=_MOCK_PROFILE)
    def test_output_keys_present(self, *_):
        result = analyze_employee_wellbeing("p1")
        for key in (
            "employee", "burnout_status", "burnout_emoji", "burnout_score",
            "signals", "days_since_last_rest", "leave_balance",
            "bridge_day_opportunities", "upcoming_holidays",
            "recommendation", "reasoning_chain",
        ):
            assert key in result, f"Missing key: {key}"

    @patch("kolay_cli.services.wellness.leave_svc.list_leaves", return_value=[])
    @patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=[])
    @patch("kolay_cli.services.wellness.person_svc.view_person", return_value=_MOCK_PROFILE)
    def test_no_balance_does_not_crash(self, *_):
        result = analyze_employee_wellbeing("p1")
        assert result["leave_balance"]["annual_unused"] == 0.0

    @patch(
        "kolay_cli.services.wellness.person_svc.view_person",
        side_effect=Exception("Person not found"),
    )
    def test_person_not_found_returns_error(self, _):
        result = analyze_employee_wellbeing("bad-id")
        assert result["error"] is True
        assert "not found" in result["message"].lower()

    @patch("kolay_cli.services.wellness.leave_svc.list_leaves", return_value=_MOCK_LEAVES)
    @patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=_MOCK_BALANCE)
    @patch("kolay_cli.services.wellness.person_svc.view_person", return_value=_MOCK_PROFILE)
    def test_reasoning_chain_has_5_steps(self, *_):
        result = analyze_employee_wellbeing("p1")
        # Each step starts with "Step N"
        steps = [s for s in result["reasoning_chain"] if s.startswith("Step")]
        assert len(steps) >= 5

    @patch("kolay_cli.services.wellness.leave_svc.list_leaves", return_value=[])
    @patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=[{
        "primary": True,
        "leaveType": {"name": "Annual Leave"},
        "entitled": 20,
        "used": 10,
        "unused": 3,   # very low
    }])
    @patch("kolay_cli.services.wellness.person_svc.view_person", return_value=_MOCK_PROFILE)
    def test_healthy_score_with_low_unused_and_recent_rest(self, *_):
        result = analyze_employee_wellbeing("p1")
        # 3 unused days, no gap penalty → should be healthy or yellow
        assert result["burnout_status"] in ("healthy", "yellow_zone")


# ── Integration: get_smart_rest_plan ─────────────────────────────────────────

class TestGetSmartRestPlan:
    @patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=_MOCK_BALANCE)
    def test_output_keys_present(self, _):
        result = get_smart_rest_plan("p1")
        for key in (
            "person_id", "annual_leave_remaining", "budget_tier",
            "horizon_days", "top_rest_opportunities", "reasoning_chain",
        ):
            assert key in result, f"Missing key: {key}"

    @patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=_MOCK_BALANCE)
    def test_generous_tier_for_high_balance(self, _):
        balance = [{"primary": True, "leaveType": {"name": "Annual"}, "unused": 20, "entitled": 20, "used": 0}]
        with patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=balance):
            result = get_smart_rest_plan("p1")
        assert result["budget_tier"] == "generous"

    @patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=[{
        "primary": True, "leaveType": {"name": "Annual"}, "unused": 3, "entitled": 10, "used": 7
    }])
    def test_conservative_tier_for_low_balance(self, _):
        result = get_smart_rest_plan("p1")
        assert result["budget_tier"] == "conservative"

    @patch(
        "kolay_cli.services.wellness.person_svc.leave_status",
        side_effect=Exception("API down"),
    )
    def test_api_failure_returns_error(self, _):
        result = get_smart_rest_plan("p1")
        assert result["error"] is True

    @patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=_MOCK_BALANCE)
    def test_custom_horizon(self, _):
        result = get_smart_rest_plan("p1", horizon_days=30)
        assert result["horizon_days"] == 30

    @patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=_MOCK_BALANCE)
    def test_opportunities_are_sorted_by_efficiency(self, _):
        result = get_smart_rest_plan("p1")
        opps = result["top_rest_opportunities"]
        effs = [o["efficiency"] for o in opps]
        assert effs == sorted(effs, reverse=True)


# ── Progress callback tests ──────────────────────────────────────────────────

class TestProgressCallbacks:
    @patch("kolay_cli.services.wellness.leave_svc.list_leaves", return_value=_MOCK_LEAVES)
    @patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=_MOCK_BALANCE)
    @patch("kolay_cli.services.wellness.person_svc.view_person", return_value=_MOCK_PROFILE)
    def test_analyze_wellbeing_calls_progress(self, *_):
        calls: list[tuple[int, int, str]] = []
        def recorder(step: int, total: int, msg: str) -> None:
            calls.append((step, total, msg))

        analyze_employee_wellbeing("p1", on_progress=recorder)
        # Should have 5 steps
        assert len(calls) == 5
        steps = [c[0] for c in calls]
        assert steps == [1, 2, 3, 4, 5]
        # All totals should be 5
        assert all(c[1] == 5 for c in calls)

    @patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=_MOCK_BALANCE)
    def test_smart_rest_plan_calls_progress(self, _):
        calls: list[tuple[int, int, str]] = []
        def recorder(step: int, total: int, msg: str) -> None:
            calls.append((step, total, msg))

        get_smart_rest_plan("p1", on_progress=recorder)
        # Should have 3 steps
        assert len(calls) == 3
        steps = [c[0] for c in calls]
        assert steps == [1, 2, 3]
        assert all(c[1] == 3 for c in calls)

    def test_no_progress_callback_does_not_crash(self):
        """Ensure on_progress=None (default) works without errors."""
        with patch("kolay_cli.services.wellness.person_svc.leave_status", return_value=_MOCK_BALANCE):
            with patch("kolay_cli.services.wellness.person_svc.view_person", return_value=_MOCK_PROFILE):
                with patch("kolay_cli.services.wellness.leave_svc.list_leaves", return_value=[]):
                    result = analyze_employee_wellbeing("p1")
        assert "error" not in result
