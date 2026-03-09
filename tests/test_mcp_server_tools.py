"""
tests/test_mcp_server_tools.py — Direct invocation of mcp_server tool functions.

Strategy: import each tool function directly from mcp_server and call it
with a mocked service layer. This avoids spinning up the FastMCP server
and covers the tool body return values (the `@require_auth` / `@mcp.tool`
decorators are bypassed by calling the underlying function).

Coverage targets: every @mcp.tool body line (75, 89, 100, 111, 135, 166, 194,
206, 235, 264, 275, 299, 334, 348, 372, 386, 410, 421, 437, 448, 469, 501,
515, 542, 556, 584, 595, 617, 638, 649, 664, 675, 689, 701, 715, 731, 750).

Also covers the @mcp.prompt bodies and person_update_fields guard branch.
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
        from kolay_cli.mcp_server import person_list
        expected = {"items": [{"id": "p1"}], "totalCount": 1}
        with patch(_svc("person_svc.list_people"), return_value=expected) as m:
            result = person_list(status="active", search=None, page=1, limit=20)
        m.assert_called_once_with(page=1, status="active", search=None, limit=20)
        assert result == expected

    def test_person_view(self):
        from kolay_cli.mcp_server import person_view
        expected = {"id": "p1", "firstName": "Alice"}
        with patch(_svc("person_svc.view_person"), return_value=expected) as m:
            result = person_view("p1")
        m.assert_called_once_with("p1")
        assert result == expected

    def test_person_summary(self):
        from kolay_cli.mcp_server import person_summary
        expected = {"firstName": "Alice"}
        with patch(_svc("person_svc.summary"), return_value=expected) as m:
            result = person_summary("p1")
        assert result == expected

    def test_person_leave_status(self):
        from kolay_cli.mcp_server import person_leave_status
        expected = [{"leaveType": {"name": "Annual"}, "unused": 10}]
        with patch(_svc("person_svc.leave_status"), return_value=expected) as m:
            result = person_leave_status("p1")
        assert result == expected

    def test_person_create(self):
        from kolay_cli.mcp_server import person_create
        expected = {"id": "new1"}
        with patch(_svc("person_svc.create_person"), return_value=expected) as m:
            result = person_create("Ali", "Veli", "ali@co.com", "2026-01-01")
        m.assert_called_once_with(
            first_name="Ali", last_name="Veli", email="ali@co.com",
            employment_start="2026-01-01", mobile_phone=None,
        )
        assert result == expected

    def test_person_update(self):
        from kolay_cli.mcp_server import person_update
        expected = {"status": "updated"}
        with patch(_svc("person_svc.update_person"), return_value=expected) as m:
            result = person_update("p1", first_name="Bob")
        m.assert_called_once_with("p1", first_name="Bob", last_name=None,
                                  email=None, mobile_phone=None, custom_fields=None)
        assert result == expected

    def test_person_terminate(self):
        from kolay_cli.mcp_server import person_terminate
        expected = {"status": "terminated"}
        with patch(_svc("person_svc.terminate_person"), return_value=expected) as m:
            result = person_terminate("p1", "2026-03-08", "03")
        m.assert_called_once_with("p1", termination_date="2026-03-08", reason_code="03")
        assert result == expected

    def test_person_rehire(self):
        from kolay_cli.mcp_server import person_rehire
        expected = {"status": "rehired"}
        with patch(_svc("person_svc.rehire_person"), return_value=expected) as m:
            result = person_rehire("p1", "2026-06-01")
        m.assert_called_once_with("p1", start_date="2026-06-01")
        assert result == expected

    def test_person_update_fields_returns_result(self):
        from kolay_cli.mcp_server import person_update_fields
        expected = {"status": "updated", "updated_fields": ["department"]}
        with patch(_svc("person_svc.update_person_fields"), return_value=expected) as m:
            result = person_update_fields("p1", {"department": "Engineering"})
        m.assert_called_once_with("p1", {"department": "Engineering"})
        assert result == expected

    def test_person_update_fields_empty_guard(self):
        """Empty update_fields dict must return error without calling the service."""
        from kolay_cli.mcp_server import person_update_fields
        with patch(_svc("person_svc.update_person_fields")) as m:
            result = person_update_fields("p1", {})
        m.assert_not_called()
        assert result["error"] is True


# ══════════════════════════════════════════════════════════════════════════════
# LEAVE TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestLeaveTools:
    def test_leave_list(self):
        from kolay_cli.mcp_server import leave_list
        expected = [{"id": "lv1"}]
        with patch(_svc("leave_svc.list_leaves"), return_value=expected) as m:
            result = leave_list(status="approved", start=None, end=None, person_id=None, limit=50)
        m.assert_called_once()
        assert result == expected

    def test_leave_view(self):
        from kolay_cli.mcp_server import leave_view
        expected = {"id": "lv1", "status": "approved"}
        with patch(_svc("leave_svc.view_leave"), return_value=expected) as m:
            result = leave_view("lv1")
        assert result == expected

    def test_leave_create(self):
        from kolay_cli.mcp_server import leave_create
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
        from kolay_cli.mcp_server import timelog_list
        expected = {"items": [], "totalCount": 0}
        with patch(_svc("timelog_svc.list_timelogs"), return_value=expected) as m:
            result = timelog_list()
        m.assert_called_once()
        assert result == expected

    def test_timelog_view(self):
        from kolay_cli.mcp_server import timelog_view
        expected = {"id": "tl1"}
        with patch(_svc("timelog_svc.view_timelog"), return_value=expected) as m:
            result = timelog_view("tl1")
        assert result == expected

    def test_timelog_create(self):
        from kolay_cli.mcp_server import timelog_create
        expected = {"status": "created"}
        with patch(_svc("timelog_svc.create_timelog"), return_value=expected) as m:
            result = timelog_create("p1", "2026-03-08 09:00:00", "2026-03-08 18:00:00")
        m.assert_called_once()
        assert result == expected

    def test_timelog_delete(self):
        from kolay_cli.mcp_server import timelog_delete
        expected = {"status": "deleted"}
        with patch(_svc("timelog_svc.delete_timelog"), return_value=expected) as m:
            result = timelog_delete("tl1")
        assert result == expected


# ══════════════════════════════════════════════════════════════════════════════
# TRAINING TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestTrainingTools:
    def test_training_list(self):
        from kolay_cli.mcp_server import training_list
        expected = {"items": [{"id": "tr1"}], "totalCount": 1}
        with patch(_svc("training_svc.list_trainings"), return_value=expected) as m:
            result = training_list()
        assert result == expected

    def test_training_view(self):
        from kolay_cli.mcp_server import training_view
        expected = {"id": "tr1", "name": "Python 101"}
        with patch(_svc("training_svc.view_training"), return_value=expected) as m:
            result = training_view("tr1")
        assert result == expected

    def test_training_create(self):
        from kolay_cli.mcp_server import training_create
        expected = {"status": "created"}
        with patch(_svc("training_svc.create_training"), return_value=expected) as m:
            result = training_create("Python 101", description="Intro to Python", duration="5")
        m.assert_called_once()
        assert result == expected

    def test_training_delete(self):
        from kolay_cli.mcp_server import training_delete
        expected = {"status": "deleted"}
        with patch(_svc("training_svc.delete_training"), return_value=expected) as m:
            result = training_delete("tr1")
        assert result == expected

    def test_person_assign_training(self):
        from kolay_cli.mcp_server import person_assign_training
        expected = {"status": "assigned"}
        with patch(_svc("person_svc.assign_training"), return_value=expected) as m:
            result = person_assign_training("p1", "tr1", status="waiting")
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
        from kolay_cli.mcp_server import transaction_list
        expected = {"items": [], "totalCount": 0}
        with patch(_svc("transaction_svc.list_transactions"), return_value=expected) as m:
            result = transaction_list()
        assert result == expected

    def test_transaction_view(self):
        from kolay_cli.mcp_server import transaction_view
        expected = {"id": "trx1"}
        with patch(_svc("transaction_svc.view_transaction"), return_value=expected) as m:
            result = transaction_view("trx1")
        assert result == expected

    def test_transaction_create(self):
        from kolay_cli.mcp_server import transaction_create
        expected = {"status": "created"}
        with patch(_svc("transaction_svc.create_transaction"), return_value=expected) as m:
            result = transaction_create("p1", "bonus", 5000.0, "2026-03-08")
        m.assert_called_once()
        assert result == expected

    def test_transaction_delete(self):
        from kolay_cli.mcp_server import transaction_delete
        expected = {"status": "deleted"}
        with patch(_svc("transaction_svc.delete_transaction"), return_value=expected) as m:
            result = transaction_delete("trx1")
        assert result == expected


# ══════════════════════════════════════════════════════════════════════════════
# CALENDAR TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestCalendarTools:
    def test_calendar_list(self):
        from kolay_cli.mcp_server import calendar_list
        expected = {"items": [], "totalCount": 0}
        with patch(_svc("calendar_svc.list_events"), return_value=expected) as m:
            result = calendar_list()
        assert result == expected

    def test_calendar_view(self):
        from kolay_cli.mcp_server import calendar_view
        expected = {"id": "ev1", "title": "Team Meeting"}
        with patch(_svc("calendar_svc.view_event"), return_value=expected) as m:
            result = calendar_view("ev1")
        assert result == expected

    def test_calendar_create(self):
        from kolay_cli.mcp_server import calendar_create
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
        from kolay_cli.mcp_server import calendar_update
        expected = {"status": "updated"}
        with patch(_svc("calendar_svc.update_event"), return_value=expected) as m:
            result = calendar_update("ev1", title="New Title")
        m.assert_called_once_with("ev1", title="New Title", start=None, end=None, comment=None)
        assert result == expected

    def test_calendar_delete(self):
        from kolay_cli.mcp_server import calendar_delete
        expected = {"status": "deleted"}
        with patch(_svc("calendar_svc.delete_event"), return_value=expected) as m:
            result = calendar_delete("ev1")
        assert result == expected


# ══════════════════════════════════════════════════════════════════════════════
# ORG / APPROVAL TOOLS
# ══════════════════════════════════════════════════════════════════════════════

class TestOrgTools:
    def test_unit_tree(self):
        from kolay_cli.mcp_server import unit_tree
        expected = [{"id": "u1", "name": "Engineering"}]
        with patch(_svc("unit_svc.unit_tree"), return_value=expected) as m:
            result = unit_tree()
        assert result == expected

    def test_approval_list(self):
        from kolay_cli.mcp_server import approval_list
        expected = [{"name": "Leave Approval"}]
        with patch(_svc("approval_svc.list_approval_processes"), return_value=expected) as m:
            result = approval_list()
        assert result == expected


# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS — exercise the return string generation
# ══════════════════════════════════════════════════════════════════════════════

class TestMcpPrompts:
    def test_employee_snapshot_returns_string(self):
        from kolay_cli.mcp_server import employee_snapshot
        result = employee_snapshot("Alice")
        assert "Alice" in result
        assert "person_list" in result

    def test_burnout_analyzer_returns_string(self):
        from kolay_cli.mcp_server import burnout_analyzer
        result = burnout_analyzer("Engineering")
        assert "Engineering" in result
        assert "person_leave_status" in result

    def test_onboarding_plan_returns_string(self):
        from kolay_cli.mcp_server import onboarding_plan
        result = onboarding_plan("Bob")
        assert "Bob" in result
        assert "person_view" in result

    def test_offboarding_plan_returns_string(self):
        from kolay_cli.mcp_server import offboarding_plan
        result = offboarding_plan("Carol")
        assert "Carol" in result
        assert "person_leave_status" in result

    def test_bulk_update_assistant_returns_string(self):
        from kolay_cli.mcp_server import bulk_update_assistant
        result = bulk_update_assistant("department", "Old Dept", "New Dept")
        assert "department" in result
        assert "Old Dept" in result
        assert "New Dept" in result
        assert "person_update_fields" in result
        # Safety guardrail must be present
        assert "CONFIRMATION" in result or "confirm" in result.lower()
