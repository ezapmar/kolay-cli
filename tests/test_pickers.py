"""
tests/test_pickers.py — Unit tests for ui/pickers.py

Strategy: test _base_pick() directly with injected mocks, bypassing the need
for a real TTY. Every public picker is an alias over _base_pick, so exercising
_base_pick with controlled inputs covers the core branch set.

Covered:
  - Normal row-number selection (index in range)
  - Raw ID passthrough (ValueError path in _base_pick)
  - Out-of-range row number (treated as raw ID)
  - Empty list → manual ID prompt
  - API error during fetch → manual ID prompt
  - Search / filter path (search_keys non-empty)
  - print_error_inline
  - Each public picker make_table is exercised via the CLI path
    (pick_person via `kolay person view` with no ID and piped row number)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from kolay_cli.cli import app

runner = CliRunner()


# ── Shared mock data ──────────────────────────────────────────────────────────

PEOPLE = [
    {"id": "p1", "firstName": "Alice", "lastName": "Smith", "workEmail": "a@co.com"},
    {"id": "p2", "firstName": "Bob", "lastName": "Jones", "workEmail": "b@co.com"},
]
LEAVE_RECORDS = [
    {"id": "lv1", "person": {"name": "Alice"}, "leaveType": {"name": "Annual"},
     "startDate": "2026-01-10", "status": "approved"},
]
TRAININGS = [
    {"id": "tr1", "name": "Python 101", "duration": 5},
]
TIMELOGS = [
    {"id": "tl1", "person": {"firstName": "Alice", "lastName": "S"}, "type": "overtime",
     "startDate": "2026-01-01 09:00:00", "status": "approved"},
]
EVENTS = [
    {"id": "ev1", "title": "Company Meeting", "start": "2026-04-01 10:00:00"},
]
TRANSACTIONS = [
    {"id": "trx1", "person": {"firstName": "Alice", "lastName": "S"}, "type": "bonus",
     "amount": 5000, "currency": "TRY", "status": "approved"},
]
FILES = [
    {"id": "f1", "name": "contract.pdf", "folderName": "HR Docs"},
]
PERSON_TRAININGS = [
    {"id": "pt1", "training": {"name": "Python 101"}, "status": "approved",
     "startDate": "2026-01-01"},
]


# ── _base_pick internal unit tests ────────────────────────────────────────────

class TestBasePick:
    """Test _base_pick directly, injecting a pre-built mock client."""

    def _make_client(self, items: list) -> MagicMock:
        """Return a mock client whose post/get returns items."""
        c = MagicMock()
        c.post.return_value = {"data": {"items": items, "totalCount": len(items)}}
        c.get.return_value = {"data": items}
        return c

    def test_row_number_returns_correct_id(self):
        from kolay_cli.ui.pickers import _base_pick
        from rich.table import Table

        client = self._make_client(PEOPLE)
        with patch("kolay_cli.ui.pickers._typer.prompt", return_value="1"):
            result = _base_pick(
                client=client,
                quips=["Fetching…"],
                prompt="Colleague",
                fetch_fn=lambda c: PEOPLE,
                table_factory=lambda items: Table(),
                confirm_fn=lambda p: f"Selected {p.get('firstName')}",
                search_keys=None,
            )
        assert result == "p1"

    def test_raw_id_passthrough(self):
        from kolay_cli.ui.pickers import _base_pick
        from rich.table import Table

        with patch("kolay_cli.ui.pickers._typer.prompt", return_value="some-uuid-1234"):
            result = _base_pick(
                client=self._make_client(PEOPLE),
                quips=["Fetching…"],
                prompt="Colleague",
                fetch_fn=lambda c: PEOPLE,
                table_factory=lambda items: Table(),
                confirm_fn=lambda p: "",
                search_keys=None,
            )
        assert result == "some-uuid-1234"

    def test_out_of_range_row_treated_as_raw_id(self):
        from kolay_cli.ui.pickers import _base_pick
        from rich.table import Table

        with patch("kolay_cli.ui.pickers._typer.prompt", return_value="999"):
            result = _base_pick(
                client=self._make_client(PEOPLE),
                quips=["Fetching…"],
                prompt="Colleague",
                fetch_fn=lambda c: PEOPLE,
                table_factory=lambda items: Table(),
                confirm_fn=lambda p: "",
                search_keys=None,
            )
        assert result == "999"

    def test_empty_list_prompts_manual_id(self):
        from kolay_cli.ui.pickers import _base_pick
        from rich.table import Table

        with patch("kolay_cli.ui.pickers._typer.prompt", return_value="manual-id"):
            result = _base_pick(
                client=self._make_client([]),
                quips=["Fetching…"],
                prompt="Colleague",
                fetch_fn=lambda c: [],
                table_factory=lambda items: Table(),
                confirm_fn=lambda p: "",
                search_keys=None,
            )
        assert result == "manual-id"

    def test_api_error_during_fetch_prompts_manual(self):
        from kolay_cli.ui.pickers import _base_pick
        from kolay_cli.api.errors import APIError
        from rich.table import Table

        def bad_fetch(c):  # type: ignore
            raise APIError("Timeout", status_code=503)

        with patch("kolay_cli.ui.pickers._typer.prompt", return_value="fallback-id"):
            result = _base_pick(
                client=self._make_client([]),
                quips=["Fetching…"],
                prompt="Colleague",
                fetch_fn=bad_fetch,
                table_factory=lambda items: Table(),
                confirm_fn=lambda p: "",
                search_keys=None,
            )
        assert result == "fallback-id"

    def test_search_filter_applied(self):
        from kolay_cli.ui.pickers import _base_pick
        from rich.table import Table

        prompts = iter(["alice", "1"])  # filter "alice", then pick row 1

        with patch("kolay_cli.ui.pickers._typer.prompt", side_effect=lambda *a, **kw: next(prompts)):
            result = _base_pick(
                client=self._make_client(PEOPLE),
                quips=["Fetching…"],
                prompt="Colleague",
                fetch_fn=lambda c: PEOPLE,
                table_factory=lambda items: Table(),
                confirm_fn=lambda p: f"Selected {p['id']}",
                search_keys=[lambda p: f"{p.get('firstName', '')} {p.get('lastName', '')}"],
            )
        # After filtering on "alice", only Alice is left → row 1 → p1
        assert result == "p1"

    def test_none_client_creates_one(self):
        """_base_pick(client=None) triggers lazy KolayClient() construction."""
        from kolay_cli.ui.pickers import _base_pick
        from rich.table import Table

        fake_client = MagicMock()
        with patch("kolay_cli.api.client.KolayClient", return_value=fake_client):
            with patch("kolay_cli.ui.pickers._typer.prompt", return_value="auto-id"):
                result = _base_pick(
                    client=None,
                    quips=["Fetching…"],
                    prompt="Item",
                    fetch_fn=lambda c: [],  # returns empty → manual fallback
                    table_factory=lambda items: Table(),
                    confirm_fn=lambda p: "",
                    search_keys=None,
                )
        assert result == "auto-id"



# ── print_error_inline ────────────────────────────────────────────────────────

def test_print_error_inline_does_not_crash():
    from kolay_cli.ui.pickers import print_error_inline
    # Should execute without raising — just prints to console
    print_error_inline("Something went wrong")


# ── CLI-level picker integration (pick_person triggered by no-arg view) ───────

class TestPickerViaCLI:
    """Test CLI commands that trigger picker when no ID is given.
    We patch pick_* directly to avoid a real TTY dependency."""

    def test_pick_person_row_1_via_cli(self, mock_client):
        """person view with no ID triggers pick_person → returns p1."""
        mock_client.get.return_value = {
            "data": {"id": "p1", "firstName": "Alice", "lastName": "Smith",
                     "status": "active", "workEmail": "a@co.com"}
        }
        with patch("kolay_cli.commands.person.pick_person", return_value="p1"):
            result = runner.invoke(app, ["person", "view"])
        assert result.exit_code == 0
        assert "Alice" in result.output

    def test_pick_person_view_json_mode(self, mock_client):
        """person view --json with explicit ID → JSON output (picker not triggered)."""
        import json
        mock_client.get.return_value = {
            "data": {"id": "p1", "firstName": "Alice", "lastName": "Smith",
                     "status": "active", "workEmail": "a@co.com"}
        }
        result = runner.invoke(app, ["--json", "person", "view", "p1"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data.get("firstName") == "Alice"

    def test_pick_leave_view_via_cli(self, mock_client):
        """leave view with no ID triggers pick_leave."""
        mock_client.get.return_value = {"data": {
            "id": "lv1", "person": {"name": "Alice"}, "leaveType": {"name": "Annual"},
            "startDate": "2026-01-10", "endDate": "2026-01-12",
            "status": "approved", "workflowLogs": [],
        }}
        with patch("kolay_cli.commands.leave.pick_leave", return_value="lv1"):
            result = runner.invoke(app, ["leave", "view"])
        assert result.exit_code == 0

    def test_pick_timelog_delete_via_cli(self, mock_client):
        """timelog delete with no ID triggers pick_timelog."""
        mock_client.delete.return_value = {"data": {}}
        with patch("kolay_cli.commands.timelog.pick_timelog", return_value="tl1"):
            result = runner.invoke(app, ["--yes", "timelog", "delete"])
        assert result.exit_code == 0

    def test_pick_training_delete_via_cli(self, mock_client):
        """training delete with no ID triggers pick_training."""
        mock_client.delete.return_value = {"data": {}}
        with patch("kolay_cli.commands.training.pick_training", return_value="tr1"):
            result = runner.invoke(app, ["--yes", "training", "delete"])
        assert result.exit_code == 0

    def test_pick_transaction_delete_via_cli(self, mock_client):
        """transaction delete with no ID triggers pick_transaction."""
        mock_client.delete.return_value = {"data": {}}
        with patch("kolay_cli.commands.transaction.pick_transaction", return_value="trx1"):
            result = runner.invoke(app, ["--yes", "transaction", "delete"])
        assert result.exit_code == 0


# ── make_table helpers — exercise table rendering for each picker ─────────────

class TestPickerTableRendering:
    """Call each picker's internal make_table (via a real _base_pick call
    with mock data) to raise line coverage of all table-building loops."""

    def _run(self, pick_fn, items, client_setup_fn=None):
        """Run a picker function with mocked client and piped '1' selection."""
        client = MagicMock()
        if client_setup_fn:
            client_setup_fn(client)
        with patch("kolay_cli.ui.pickers._typer.prompt", side_effect=["", "1"]):
            try:
                return pick_fn(client)
            except Exception:
                return None  # out-of-range or other edge — just exercising the table

    def test_pick_person_table(self):
        from kolay_cli.ui.pickers import pick_person
        client = MagicMock()
        client.post.return_value = {"data": {"items": PEOPLE, "totalCount": 2}}
        with patch("kolay_cli.ui.pickers._typer.prompt", side_effect=["", "1"]):
            result = pick_person(client)
        assert result == "p1"

    def test_pick_leave_table(self):
        from kolay_cli.ui.pickers import pick_leave
        client = MagicMock()
        client.get.return_value = {"data": LEAVE_RECORDS}
        with patch("kolay_cli.ui.pickers._typer.prompt", side_effect=["", "1"]):
            result = pick_leave(client)
        assert result == "lv1"

    def test_pick_transaction_table(self):
        from kolay_cli.ui.pickers import pick_transaction
        client = MagicMock()
        client.post.return_value = {"data": {"items": TRANSACTIONS}}
        with patch("kolay_cli.ui.pickers._typer.prompt", side_effect=["", "1"]):
            result = pick_transaction(client)
        assert result == "trx1"

    def test_pick_event_table(self):
        from kolay_cli.ui.pickers import pick_event
        client = MagicMock()
        client.get.return_value = {"data": {"items": EVENTS}}
        with patch("kolay_cli.ui.pickers._typer.prompt", side_effect=["", "1"]):
            result = pick_event(client)
        assert result == "ev1"

    def test_pick_timelog_table(self):
        from kolay_cli.ui.pickers import pick_timelog
        client = MagicMock()
        client.post.return_value = {"data": {"items": TIMELOGS}}
        with patch("kolay_cli.ui.pickers._typer.prompt", side_effect=["", "1"]):
            result = pick_timelog(client)
        assert result == "tl1"

    def test_pick_training_table(self):
        from kolay_cli.ui.pickers import pick_training
        client = MagicMock()
        client.get.return_value = {"data": {"items": TRAININGS}}
        with patch("kolay_cli.ui.pickers._typer.prompt", side_effect=["", "1"]):
            result = pick_training(client)
        assert result == "tr1"

    def test_pick_person_training_table(self):
        from kolay_cli.ui.pickers import pick_person_training
        person_client = MagicMock()
        person_client.post.return_value = {"data": {"items": PEOPLE, "totalCount": 2}}
        person_client.get.return_value = {"data": PERSON_TRAININGS}
        # First prompt picks the person (row 1), second picks the training (row 1)
        with patch("kolay_cli.ui.pickers._typer.prompt", side_effect=["", "1", "1"]):
            result = pick_person_training(person_client)
        assert result == "pt1"

    def test_pick_person_file_table(self):
        from kolay_cli.ui.pickers import pick_person_file
        client = MagicMock()
        client.post.return_value = {"data": {"items": PEOPLE, "totalCount": 2}}
        client.get.return_value = {"data": FILES}
        # person filter + person pick + file filter + file pick
        with patch("kolay_cli.ui.pickers._typer.prompt", side_effect=["", "1", "", "1"]):
            result = pick_person_file(client)
        assert result == "f1"
