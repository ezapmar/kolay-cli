"""
Tests for dead-end error recovery improvements.

Validates that mutating commands (terminate, rehire, create_person,
create_leave, create_timelog, create_transaction) offer actionable
recovery options instead of dead-ending on API errors.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from kolay_cli.cli import app
from kolay_cli.api.errors import APIError

runner = CliRunner()

PERSON_LIST_RESPONSE = {
    "data": {
        "items": [
            {
                "id": "abc123def456abc123def456abc12345",
                "firstName": "Bora",
                "lastName": "Ağaoğlu",
                "workEmail": "bora@example.com",
                "status": "active",
            }
        ],
        "totalCount": 1,
    }
}

PERSON_VIEW_RESPONSE = {
    "data": {
        "person": {
            "id": "abc123def456abc123def456abc12345",
            "firstName": "Bora",
            "lastName": "Ağaoğlu",
            "workEmail": "bora@example.com",
            "status": "active",
        }
    }
}

PENDING_APPROVAL_MSG = (
    "Çalışana tanımlı onay bekleyen talep(ler) mevcut. "
    "Lütfen onaylayıp, reddedip veya silip tekrar deneyin."
)

PERSON_ID = "abc123def456abc123def456abc12345"


# ── Terminate Recovery ────────────────────────────────────────────────────────

class TestTerminateRecovery:

    def test_terminate_pending_approvals_shows_tip_and_menu(self, mock_client):
        """On pending-approval error, show a helpful tip and recovery menu."""
        from kolay_cli.ui.output import set_yes_mode
        set_yes_mode(True)

        mock_client.get.return_value = PERSON_VIEW_RESPONSE
        mock_client.post.side_effect = [
            APIError(PENDING_APPROVAL_MSG, status_code=400),  # terminate fails
            {"data": []},  # leave list in recovery handler
        ]

        result = runner.invoke(
            app,
            ["person", "terminate", PERSON_ID,
             "--termination-date", "2026-03-09", "--reason", "03"],
            input="4\n",  # abort
        )

        # Should show the tip about pending requests
        assert (
            "pending" in result.output.lower()
            or "talep" in result.output.lower()
            or "tip" in result.output.lower()
        )
        # Menu should offer options
        assert "1" in result.output and "2" in result.output

    def test_terminate_abort_on_error_exits_1(self, mock_client):
        """Choosing abort (4) after a termination error exits with code 1."""
        from kolay_cli.ui.output import set_yes_mode
        set_yes_mode(True)

        mock_client.get.return_value = PERSON_VIEW_RESPONSE
        mock_client.post.side_effect = APIError(
            "Some other error", status_code=400
        )

        result = runner.invoke(
            app,
            ["person", "terminate", PERSON_ID,
             "--termination-date", "2026-03-09", "--reason", "03"],
            input="4\n",  # abort
        )

        assert result.exit_code == 1

    def test_terminate_success_still_works(self, mock_client):
        """Happy path: successful termination still shows success message."""
        from kolay_cli.ui.output import set_yes_mode
        set_yes_mode(True)

        mock_client.get.return_value = PERSON_VIEW_RESPONSE
        mock_client.post.return_value = {"data": {"status": "terminated"}}

        result = runner.invoke(
            app,
            ["person", "terminate", PERSON_ID,
             "--termination-date", "2026-03-09", "--reason", "03"],
        )

        assert result.exit_code == 0
        assert "terminated" in result.output.lower() or "success" in result.output.lower()

    def test_terminate_without_errors_shows_no_recovery_menu(self, mock_client):
        """When terminate succeeds, no recovery menu is shown."""
        from kolay_cli.ui.output import set_yes_mode
        set_yes_mode(True)

        mock_client.get.return_value = PERSON_VIEW_RESPONSE
        mock_client.post.return_value = {"data": {"status": "terminated"}}

        result = runner.invoke(
            app,
            ["person", "terminate", PERSON_ID,
             "--termination-date", "2026-03-09", "--reason", "03"],
        )

        assert "Choose an option" not in result.output
        assert result.exit_code == 0


# ── Rehire Recovery ───────────────────────────────────────────────────────────

class TestRehireRecovery:

    def test_rehire_error_shows_view_hint(self, mock_client):
        """On rehire error, show a hint to check the employee's current status."""
        mock_client.post.side_effect = APIError("Employee is already active.", status_code=400)

        result = runner.invoke(
            app,
            ["person", "rehire", PERSON_ID, "--start-date", "2026-03-10"],
        )

        # 400 errors map to exit code 2 per EXIT_CODES
        assert result.exit_code in (1, 2)
        assert "kolay person view" in result.output or "status" in result.output.lower()

    def test_rehire_success_works(self, mock_client):
        """Happy path: rehire succeeds."""
        mock_client.post.return_value = {"data": {"status": "rehired"}}

        result = runner.invoke(
            app,
            ["person", "rehire", PERSON_ID, "--start-date", "2026-03-10"],
        )

        assert result.exit_code == 0
        assert "rehired" in result.output.lower() or "success" in result.output.lower()


# ── Create Person Recovery ────────────────────────────────────────────────────

class TestCreatePersonRecovery:

    def test_create_person_duplicate_email_hint(self, mock_client):
        """On 409 from person create, show a hint about duplicate email."""
        mock_client.post.side_effect = APIError(
            "A person with this email already exists.", status_code=409
        )

        result = runner.invoke(
            app,
            ["person", "create",
             "--first-name", "Jane", "--last-name", "Doe",
             "--email", "jane@example.com", "--start-date", "2026-01-01"],
        )

        # Should not just dump a generic error — show the email-specific hint
        assert "jane@example.com" in result.output
        assert "search" in result.output.lower() or "exists" in result.output.lower() or "may" in result.output.lower()

    def test_create_person_success(self, mock_client):
        """Happy path: person create works."""
        mock_client.post.return_value = {"data": {"id": "new-person-id"}}

        result = runner.invoke(
            app,
            ["person", "create",
             "--first-name", "Jane", "--last-name", "Doe",
             "--email", "jane@example.com", "--start-date", "2026-01-01"],
        )

        assert result.exit_code == 0
        assert "created" in result.output.lower()


# ── Leave Create Recovery ─────────────────────────────────────────────────────

class TestLeaveCreateRecovery:

    def test_create_leave_error_offers_abort(self, mock_client):
        """On leave create error, user is offered retry/abort options; abort exits 1."""
        leave_types = [
            {
                "leaveTypeId": "lt1",
                "leaveType": {"name": "Annual Leave"},
                "unused": 5,
            }
        ]
        mock_client.get.side_effect = [
            {"data": leave_types},  # leave_status call
        ]
        mock_client.post.side_effect = [
            APIError("Overlapping leave request exists.", status_code=400),
        ]

        result = runner.invoke(
            app,
            ["leave", "create",
             "--person-id", PERSON_ID,
             "--type-id", "lt1",
             "--start", "2026-03-10", "--end", "2026-03-11"],
            input="3\n",  # abort
        )

        assert result.exit_code == 1

    def test_create_leave_menu_shows_options(self, mock_client):
        """On leave create error, recovery menu is displayed."""
        leave_types = [{"leaveTypeId": "lt1", "leaveType": {"name": "Annual Leave"}, "unused": 5}]
        mock_client.get.return_value = {"data": leave_types}
        mock_client.post.side_effect = [
            APIError("overlap", status_code=400),
        ]

        result = runner.invoke(
            app,
            ["leave", "create",
             "--person-id", PERSON_ID,
             "--type-id", "lt1",
             "--start", "2026-03-10", "--end", "2026-03-11"],
            input="3\n",  # abort
        )

        # Recovery options should appear
        assert "1" in result.output  # option 1: try different dates
        assert "2" in result.output  # option 2: check balance

    def test_create_leave_success_without_error(self, mock_client):
        """Happy path: leave create works when API succeeds."""
        leave_types = [{"leaveTypeId": "lt1", "leaveType": {"name": "Annual Leave"}, "unused": 10}]
        mock_client.get.return_value = {"data": leave_types}
        mock_client.post.return_value = {"data": {"status": "created"}}

        result = runner.invoke(
            app,
            ["leave", "create",
             "--person-id", PERSON_ID,
             "--type-id", "lt1",
             "--start", "2026-03-10", "--end", "2026-03-11"],
        )

        assert result.exit_code == 0
        assert "success" in result.output.lower() or "submitted" in result.output.lower()


# ── Timelog Create Recovery ───────────────────────────────────────────────────

class TestTimelogCreateRecovery:

    def test_create_timelog_error_offers_retry_and_abort(self, mock_client):
        """On timelog create error, offer retry with different times or abort."""
        mock_client.post.side_effect = [
            APIError("Overlapping timelog entry.", status_code=400),
        ]

        result = runner.invoke(
            app,
            ["timelog", "create",
             "--person-id", PERSON_ID,
             "--start", "2026-03-10 09:00:00",
             "--end", "2026-03-10 17:00:00"],
            input="2\n",  # abort
        )

        assert result.exit_code == 1
        assert (
            "overlap" in result.output.lower()
            or "tip" in result.output.lower()
            or "1" in result.output  # option 1: try different times
        )

    def test_create_timelog_success(self, mock_client):
        """Happy path: timelog create works when API succeeds."""
        mock_client.post.return_value = {"data": {"id": "tl1"}}

        result = runner.invoke(
            app,
            ["timelog", "create",
             "--person-id", PERSON_ID,
             "--start", "2026-03-10 09:00:00",
             "--end", "2026-03-10 17:00:00"],
        )

        assert result.exit_code == 0
        assert "submitted" in result.output.lower() or "approval" in result.output.lower()


# ── Transaction Create Recovery ───────────────────────────────────────────────

class TestTransactionCreateRecovery:

    def test_create_transaction_error_offers_retry(self, mock_client):
        """On transaction create error, offer retry options."""
        mock_client.post.side_effect = [
            APIError("Invalid transaction amount.", status_code=400),
        ]

        result = runner.invoke(
            app,
            ["transaction", "create",
             "--person-id", PERSON_ID,
             "--type", "bonus", "--amount", "100",
             "--date", "2026-03-10"],
            input="3\n",  # abort
        )

        assert result.exit_code == 1
        assert "1" in result.output or "amount" in result.output.lower()

    def test_create_transaction_success(self, mock_client):
        """Happy path: transaction create works when API succeeds."""
        mock_client.post.return_value = {"data": {"id": "trx1"}}

        result = runner.invoke(
            app,
            ["transaction", "create",
             "--person-id", PERSON_ID,
             "--type", "bonus", "--amount", "500",
             "--date", "2026-03-10"],
        )

        assert result.exit_code == 0
        assert "success" in result.output.lower() or "created" in result.output.lower()


# ── recoverable_api_call Unit Test ────────────────────────────────────────────

class TestRecoverableApiCall:

    def test_reraises_api_error(self, monkeypatch):
        """recoverable_api_call does not swallow APIError — it re-raises it."""
        from kolay_cli.ui.formatters import recoverable_api_call
        from kolay_cli.ui import output as _out

        monkeypatch.setattr("kolay_cli.ui.formatters.print_api_error", lambda exc: None)
        monkeypatch.setattr(_out, "is_json_mode", lambda: False)

        with pytest.raises(APIError):
            with recoverable_api_call("Testing..."):
                raise APIError("test error", status_code=400)

    def test_does_not_raise_on_success(self):
        """recoverable_api_call yields normally on success."""
        from kolay_cli.ui.formatters import recoverable_api_call

        captured = []
        with recoverable_api_call("Testing..."):
            captured.append(42)

        assert captured == [42]
