"""
tests/test_mcp_server_tools.py — Direct invocation of mcp_server tool functions.

Strategy: import each tool function directly from mcp_server and call it
with a mocked service layer. This avoids spinning up the FastMCP server
and covers the tool body return values (the `@require_auth` / `@mcp.tool`
decorators are bypassed by calling the underlying function).

Coverage targets: every @mcp.tool body line (75, 89, 100, 111, 135, 166, 194,
206, 235, 264, 275, 299, 334, 348, 372, 386, 410, 421, 437, 448, 469, 501,
515, 542, 556, 584, 595, 617, 638, 649, 664, 675, 689, 701, 715, 731, 750).

Also covers the @mcp.prompt bodies and person_update extra_fields guard branch.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── Helper: patch all service modules ────────────────────────────────────────

def _svc(name: str) -> str:
    return f"kolay_cli.mcp_server.{name}"


# ══════════════════════════════════════════════════════════════════════════════
# PEOPLE TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestPersonTools:
    def test_person_list(self):
        from kolay_cli.mcp.tools_people import person_list
        expected = {"items": [{"id": "p1"}], "totalCount": 1}
        with patch(_svc("person_svc.list_people"), return_value=expected) as m:
            result = person_list(status="active", search=None, page=1, limit=20)
        m.assert_called_once_with(page=1, status="active", search=None, limit=20)
        assert result == expected

    def test_person_view(self):
        import asyncio
        from unittest.mock import AsyncMock, MagicMock
        from kolay_cli.mcp.tools_people import person_view
        expected = {"id": "p1", "firstName": "Alice"}
        mock_ctx = MagicMock()
        mock_ctx.set_state = AsyncMock()
        with patch(_svc("person_svc.view_person"), return_value=expected) as m:
            result = asyncio.run(person_view("p1", ctx=mock_ctx))
        m.assert_called_once_with("p1")
        assert result == expected

    def test_person_summary(self):
        from kolay_cli.mcp.tools_people import person_summary
        expected = {"firstName": "Alice"}
        with patch(_svc("person_svc.summary"), return_value=expected) as m:
            result = person_summary("p1")
        assert result == expected

    def test_person_leave_status(self):
        from kolay_cli.mcp.tools_people import person_leave_status
        expected = [{"leaveType": {"name": "Annual"}, "unused": 10}]
        with patch(_svc("person_svc.leave_status"), return_value=expected) as m:
            result = person_leave_status("p1")
        assert result == expected

    def test_person_create(self):
        from kolay_cli.mcp.tools_people import person_create
        expected = {"id": "new1"}
        with patch(_svc("person_svc.create_person"), return_value=expected) as m:
            result = person_create("Ali", "Veli", "ali@co.com", "2026-01-01")
        m.assert_called_once_with(
            first_name="Ali", last_name="Veli", email="ali@co.com",
            employment_start="2026-01-01", mobile_phone=None,
        )
        assert result == expected

    def test_person_update(self):
        from kolay_cli.mcp.tools_people import person_update
        expected = {"status": "updated"}
        with patch(_svc("person_svc.update_person"), return_value=expected) as m:
            result = person_update("p1", first_name="Bob")
        m.assert_called_once_with("p1", first_name="Bob", last_name=None,
                                  email=None, mobile_phone=None, custom_fields=None)
        assert result == expected

    def test_person_terminate(self):
        import asyncio
        from kolay_cli.mcp.tools_people import person_terminate
        from unittest.mock import AsyncMock, MagicMock
        expected = {"status": "terminated"}
        mock_ctx = MagicMock()
        elicit_result = MagicMock(action="accept", data=True)
        mock_ctx.elicit = AsyncMock(return_value=elicit_result)
        with patch(_svc("person_svc.view_person"), return_value={"firstName": "Jane", "lastName": "Doe"}), \
             patch(_svc("person_svc.terminate_person"), return_value=expected) as m:
            result = asyncio.run(person_terminate("p1", "2026-03-08", "03", ctx=mock_ctx))
        m.assert_called_once_with("p1", termination_date="2026-03-08", reason_code="03")
        assert result == expected

    def test_person_rehire(self):
        from kolay_cli.mcp.tools_people import person_rehire
        expected = {"status": "rehired"}
        with patch(_svc("person_svc.rehire_person"), return_value=expected) as m:
            result = person_rehire("p1", "2026-06-01")
        m.assert_called_once_with("p1", start_date="2026-06-01")
        assert result == expected

    def test_person_update_extra_fields_returns_result(self):
        from kolay_cli.mcp.tools_people import person_update
        expected = {"status": "updated", "updated_fields": ["department"]}
        with patch(_svc("person_svc.update_person_fields"), return_value=expected) as m:
            result = person_update("p1", extra_fields={"department": "Engineering"})
        m.assert_called_once_with("p1", {"department": "Engineering"})
        assert result == expected

    def test_person_update_empty_extra_fields_guard(self):
        """Empty extra_fields dict must return error without calling the service."""
        from kolay_cli.mcp.tools_people import person_update
        with patch(_svc("person_svc.update_person_fields")) as m:
            result = person_update("p1", extra_fields={})
        m.assert_not_called()
        assert result["error"] is True


# ══════════════════════════════════════════════════════════════════════════════
# LEAVE TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestLeaveTools:
    def test_leave_list(self):
        from kolay_cli.mcp.tools_leaves import leave_list
        expected = [{"id": "lv1"}]
        with patch(_svc("leave_svc.list_leaves"), return_value=expected) as m:
            result = leave_list(status="approved", start=None, end=None, person_id=None, limit=50)
        m.assert_called_once()
        assert result == expected

    def test_leave_view(self):
        from kolay_cli.mcp.tools_leaves import leave_view
        expected = {"id": "lv1", "status": "approved"}
        with patch(_svc("leave_svc.view_leave"), return_value=expected) as m:
            result = leave_view("lv1")
        assert result == expected

    def test_leave_create(self):
        from kolay_cli.mcp.tools_leaves import leave_create
        expected = {"status": "created"}
        with patch(_svc("leave_svc.create_leave"), return_value=expected) as m:
            result = leave_create("p1", "lt1", "2026-03-10", "2026-03-12")
        m.assert_called_once()
        assert result == expected


# ══════════════════════════════════════════════════════════════════════════════
# TIMELOG TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestTimelogTools:
    def test_timelog_list(self):
        from kolay_cli.mcp.tools_time import timelog_list
        expected = {"items": [], "totalCount": 0}
        with patch(_svc("timelog_svc.list_timelogs"), return_value=expected) as m:
            result = timelog_list()
        m.assert_called_once()
        assert result == expected

    def test_timelog_view(self):
        from kolay_cli.mcp.tools_time import timelog_view
        expected = {"id": "tl1"}
        with patch(_svc("timelog_svc.view_timelog"), return_value=expected) as m:
            result = timelog_view("tl1")
        assert result == expected

    def test_timelog_create(self):
        from kolay_cli.mcp.tools_time import timelog_create
        expected = {"status": "created"}
        with patch(_svc("timelog_svc.create_timelog"), return_value=expected) as m:
            result = timelog_create("p1", "2026-03-08 09:00:00", "2026-03-08 18:00:00")
        m.assert_called_once()
        assert result == expected

    def test_timelog_delete(self):
        from kolay_cli.mcp.tools_time import timelog_delete
        expected = {"status": "deleted"}
        with patch(_svc("timelog_svc.delete_timelog"), return_value=expected) as m:
            result = timelog_delete("tl1")
        assert result == expected


# ══════════════════════════════════════════════════════════════════════════════
# TRAINING TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestTrainingTools:
    def test_training_list(self):
        from kolay_cli.mcp.tools_training import training_list
        expected = {"items": [{"id": "tr1"}], "totalCount": 1}
        with patch(_svc("training_svc.list_trainings"), return_value=expected) as m:
            result = training_list()
        assert result == expected

    def test_training_view(self):
        from kolay_cli.mcp.tools_training import training_view
        expected = {"id": "tr1", "name": "Python 101"}
        with patch(_svc("training_svc.view_training"), return_value=expected) as m:
            result = training_view("tr1")
        assert result == expected

    def test_training_create(self):
        from kolay_cli.mcp.tools_training import training_create
        expected = {"status": "created"}
        with patch(_svc("training_svc.create_training"), return_value=expected) as m:
            result = training_create("Python 101", description="Intro to Python", duration="5")
        m.assert_called_once()
        assert result == expected

    def test_training_delete(self):
        import asyncio
        from kolay_cli.mcp.tools_training import training_delete
        from unittest.mock import AsyncMock, MagicMock
        expected = {"status": "deleted"}
        mock_ctx = MagicMock()
        elicit_result = MagicMock(action="accept", data=True)
        mock_ctx.elicit = AsyncMock(return_value=elicit_result)
        with patch(_svc("training_svc.view_training"), return_value={"name": "Safety Training"}), \
             patch(_svc("training_svc.delete_training"), return_value=expected) as m:
            result = asyncio.run(training_delete("tr1", ctx=mock_ctx))
        m.assert_called_once_with("tr1")
        assert result == expected

    def test_person_training_manage(self):
        from kolay_cli.mcp.tools_training import person_training_manage
        expected = {"status": "assigned"}
        with patch(_svc("person_svc.assign_training"), return_value=expected) as m:
            result = person_training_manage("assign", person_id="p1", training_id="tr1", status="waiting")
        m.assert_called_once_with(
            person_id="p1", training_id="tr1", status="waiting",
            start_date=None, end_date=None,
        )
        assert result == expected


# ══════════════════════════════════════════════════════════════════════════════
# TRANSACTION TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestTransactionTools:
    def test_transaction_list(self):
        from kolay_cli.mcp.tools_finance import transaction_list
        expected = {"items": [], "totalCount": 0}
        with patch(_svc("transaction_svc.list_transactions"), return_value=expected) as m:
            result = transaction_list()
        assert result == expected

    def test_transaction_view(self):
        from kolay_cli.mcp.tools_finance import transaction_view
        expected = {"id": "trx1"}
        with patch(_svc("transaction_svc.view_transaction"), return_value=expected) as m:
            result = transaction_view("trx1")
        assert result == expected

    def test_transaction_create(self):
        from kolay_cli.mcp.tools_finance import transaction_create
        expected = {"status": "created"}
        with patch(_svc("transaction_svc.create_transaction"), return_value=expected) as m:
            result = transaction_create("p1", "bonus", 5000.0, "2026-03-08")
        m.assert_called_once()
        assert result == expected

    def test_transaction_delete(self):
        from kolay_cli.mcp.tools_finance import transaction_delete
        expected = {"status": "deleted"}
        with patch(_svc("transaction_svc.delete_transaction"), return_value=expected) as m:
            result = transaction_delete("trx1")
        assert result == expected


# ══════════════════════════════════════════════════════════════════════════════
# CALENDAR TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestCalendarTools:
    def test_calendar_list(self):
        from kolay_cli.mcp.tools_org import calendar_list
        expected = {"items": [], "totalCount": 0}
        with patch(_svc("calendar_svc.list_events"), return_value=expected) as m:
            result = calendar_list()
        assert result == expected

    def test_calendar_view(self):
        from kolay_cli.mcp.tools_org import calendar_view
        expected = {"id": "ev1", "title": "Team Meeting"}
        with patch(_svc("calendar_svc.view_event"), return_value=expected) as m:
            result = calendar_view("ev1")
        assert result == expected

    def test_calendar_create(self):
        from kolay_cli.mcp.tools_org import calendar_create
        expected = {"id": "ev_new"}
        with patch(_svc("calendar_svc.create_event"), return_value=expected) as m:
            result = calendar_create("Team Meeting", "2026-04-01 10:00:00", "2026-04-01 11:00:00")
        m.assert_called_once_with(
            title="Team Meeting",
            start="2026-04-01 10:00:00",
            end="2026-04-01 11:00:00",
            comment="",
        )
        assert result == expected

    def test_calendar_update(self):
        from kolay_cli.mcp.tools_org import calendar_update
        expected = {"status": "updated"}
        with patch(_svc("calendar_svc.update_event"), return_value=expected) as m:
            result = calendar_update("ev1", title="New Title")
        m.assert_called_once_with("ev1", title="New Title", start=None, end=None, comment=None)
        assert result == expected

    def test_calendar_delete(self):
        from kolay_cli.mcp.tools_org import calendar_delete
        expected = {"status": "deleted"}
        with patch(_svc("calendar_svc.delete_event"), return_value=expected) as m:
            result = calendar_delete("ev1")
        assert result == expected


# ══════════════════════════════════════════════════════════════════════════════
# ORG / APPROVAL TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestOrgTools:
    def test_unit_tree(self):
        from kolay_cli.mcp.tools_org import unit_tree
        expected = [{"id": "u1", "name": "Engineering"}]
        with patch(_svc("unit_svc.unit_tree"), return_value=expected) as m:
            result = unit_tree()
        assert result == expected

    def test_approval_list(self):
        from kolay_cli.mcp.tools_org import approval_list
        expected = [{"name": "Leave Approval"}]
        with patch(_svc("approval_svc.list_approval_processes"), return_value=expected) as m:
            result = approval_list()
        assert result == expected


# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS — exercise the return string generation
# ══════════════════════════════════════════════════════════════════════════════

class TestMcpPrompts:
    def test_employee_snapshot_returns_string(self):
        from kolay_cli.mcp.prompts import employee_snapshot
        result = employee_snapshot("Alice")
        assert "Alice" in result
        assert "person_list" in result

    def test_burnout_analyzer_returns_string(self):
        from kolay_cli.mcp.prompts import burnout_analyzer
        result = burnout_analyzer("Engineering")
        assert "Engineering" in result
        assert "person_leave_status" in result

    def test_onboarding_plan_returns_string(self):
        from kolay_cli.mcp.prompts import onboarding_plan
        result = onboarding_plan("Bob")
        assert "Bob" in result
        assert "person_view" in result

    def test_offboarding_plan_returns_string(self):
        from kolay_cli.mcp.prompts import offboarding_plan
        result = offboarding_plan("Carol")
        assert "Carol" in result
        assert "person_leave_status" in result

    def test_bulk_update_assistant_returns_string(self):
        from kolay_cli.mcp.prompts import bulk_update_assistant
        result = bulk_update_assistant("department", "Old Dept", "New Dept")
        assert "department" in result
        assert "Old Dept" in result
        assert "New Dept" in result
        assert "person_update" in result
        # Safety guardrail must be present
        assert "CONFIRMATION" in result or "confirm" in result.lower()


# ══════════════════════════════════════════════════════════════════════════════
# PAYROLL TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestPayrollTools:
    def test_payroll_sheet_view(self):
        from kolay_cli.mcp.tools_finance import payroll_sheet_view
        expected = {"items": [{"person": {"firstName": "Ali", "lastName": "Veli"}, "gross": 10000}]}
        with patch(_svc("payroll_svc.view_payroll_sheet"), return_value=expected) as m:
            result = payroll_sheet_view("abc123")
        m.assert_called_once_with("abc123", search=None, status=None, salary_period=None)
        assert result == expected

    def test_payroll_sheet_view_with_match(self):
        from kolay_cli.mcp.tools_finance import payroll_sheet_view
        data = {"items": [
            {"person": {"firstName": "Ali", "lastName": "Veli"}, "gross": 10000},
            {"person": {"firstName": "Ayşe", "lastName": "Kaya"}, "gross": 12000},
        ]}
        with patch(_svc("payroll_svc.view_payroll_sheet"), return_value=data):
            result = payroll_sheet_view("abc123", match="Ali")
        # Only Ali should remain after client-side filter
        assert len(result["items"]) == 1
        assert result["items"][0]["person"]["firstName"] == "Ali"

    def test_payroll_sheet_view_with_search(self):
        from kolay_cli.mcp.tools_finance import payroll_sheet_view
        expected = {"items": []}
        with patch(_svc("payroll_svc.view_payroll_sheet"), return_value=expected) as m:
            result = payroll_sheet_view("abc123", search="Ali", status=["ended"])
        m.assert_called_once_with("abc123", search="Ali", status=["ended"], salary_period=None)
        assert result == expected


# ══════════════════════════════════════════════════════════════════════════════
# WELLBEING ENGINE TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestWellbeingTools:
    def test_analyze_employee_wellbeing_delegates_to_service(self):
        import asyncio
        from kolay_cli.mcp.tools_wellness import analyze_employee_wellbeing
        expected = {
            "employee": {"id": "p1", "name": "Ayse Yilmaz"},
            "burnout_status": "red_zone",
            "burnout_score": 5,
        }
        with patch(_svc("wellness_svc.analyze_employee_wellbeing"), return_value=expected) as m:
            result = analyze_employee_wellbeing("p1")
        m.assert_called_once()
        assert result == expected

    def test_analyze_employee_wellbeing_passes_person_id(self):
        import asyncio
        from kolay_cli.mcp.tools_wellness import analyze_employee_wellbeing
        with patch(_svc("wellness_svc.analyze_employee_wellbeing"), return_value={}) as m:
            analyze_employee_wellbeing("some-uuid-123")
        m.assert_called_once()
        assert m.call_args[0][0] == "some-uuid-123"

    def test_get_smart_rest_plan_delegates_to_service(self):
        import asyncio
        from kolay_cli.mcp.tools_wellness import get_smart_rest_plan
        expected = {
            "person_id": "p1",
            "budget_tier": "generous",
            "top_rest_opportunities": [],
        }
        with patch(_svc("wellness_svc.get_smart_rest_plan"), return_value=expected) as m:
            result = get_smart_rest_plan("p1")
        m.assert_called_once()
        assert result == expected

    def test_get_smart_rest_plan_custom_horizon(self):
        import asyncio
        from kolay_cli.mcp.tools_wellness import get_smart_rest_plan
        with patch(_svc("wellness_svc.get_smart_rest_plan"), return_value={}) as m:
            get_smart_rest_plan("p1", horizon_days=30)
        m.assert_called_once()

    def test_get_smart_rest_plan_default_horizon_is_90(self):
        from kolay_cli.mcp.tools_wellness import get_smart_rest_plan
        import inspect
        sig = inspect.signature(get_smart_rest_plan)
        assert sig.parameters["horizon_days"].default == 90


# ══════════════════════════════════════════════════════════════════════════════
# NEW PROMPTS: wellbeing_briefing, hr_trend_analysis, risk_brief
# ══════════════════════════════════════════════════════════════════════════════

class TestNewPrompts:
    def test_wellbeing_briefing_contains_tools(self):
        from kolay_cli.mcp.prompts import wellbeing_briefing
        result = wellbeing_briefing("Ayse")
        assert "analyze_employee_wellbeing" in result
        assert "get_smart_rest_plan" in result
        assert "Ayse" in result

    def test_wellbeing_briefing_has_table_template(self):
        from kolay_cli.mcp.prompts import wellbeing_briefing
        result = wellbeing_briefing()
        # Should contain the table headers
        assert "Bridge Day" in result
        assert "Efficiency" in result

    def test_hr_trend_analysis_contains_tools(self):
        from kolay_cli.mcp.prompts import hr_trend_analysis
        result = hr_trend_analysis("Engineering")
        assert "turnover_risk_scan" in result
        assert "payroll_anomaly_detect" in result
        assert "Engineering" in result

    def test_hr_trend_analysis_has_sections(self):
        from kolay_cli.mcp.prompts import hr_trend_analysis
        result = hr_trend_analysis()
        assert "Retention" in result or "Burnout" in result
        assert "Payroll" in result

    def test_manager_dashboard_returns_string(self):
        from kolay_cli.mcp.prompts import manager_dashboard
        result = manager_dashboard("Sales")
        assert "Sales" in result
        assert "person_list" in result or "leave" in result.lower()
