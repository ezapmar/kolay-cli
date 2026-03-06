"""Tests for `kolay calendar` commands."""
from typer.testing import CliRunner
from kolay_cli.cli import app

runner = CliRunner()

EVENT_LIST_RESPONSE = {
    "data": {
        "items": [
            {
                "id": "ev1",
                "title": "Team Standup",
                "start": "2025-06-01 09:00:00",
                "end": "2025-06-01 09:30:00",
            },
            {
                "id": "ev2",
                "title": "Sprint Review",
                "start": "2025-06-05 14:00:00",
                "end": "2025-06-05 15:00:00",
            },
        ],
        "totalCount": 2,
    }
}

EVENT_VIEW_RESPONSE = {
    "data": {
        "id": "ev1",
        "title": "Team Standup",
        "start": "2025-06-01 09:00:00",
        "end": "2025-06-01 09:30:00",
        "comment": "Daily sync",
    }
}


# ── list ──────────────────────────────────────────────────────────────────────

def test_calendar_list(mock_client):
    mock_client.get.return_value = EVENT_LIST_RESPONSE
    result = runner.invoke(app, ["calendar", "list"])
    assert result.exit_code == 0
    assert "Team Standup" in result.output
    assert "Sprint Review" in result.output


def test_calendar_list_empty(mock_client):
    mock_client.get.return_value = {"data": {"items": [], "totalCount": 0}}
    result = runner.invoke(app, ["calendar", "list"])
    assert result.exit_code == 0
    assert "No events found" in result.output


def test_calendar_list_with_date_flags(mock_client):
    mock_client.get.return_value = {"data": {"items": [], "totalCount": 0}}
    result = runner.invoke(app, [
        "calendar", "list",
        "--start", "2025-01-01",
        "--end", "2025-12-31",
    ])
    assert result.exit_code == 0
    params = mock_client.get.call_args[1]["params"]
    assert "2025-01-01" in params["start"]
    assert "2025-12-31" in params["end"]


def test_calendar_list_with_search(mock_client):
    mock_client.get.return_value = {"data": {"items": [], "totalCount": 0}}
    result = runner.invoke(app, ["calendar", "list", "--search", "standup"])
    assert result.exit_code == 0
    params = mock_client.get.call_args[1]["params"]
    assert params["search"] == "standup"


# ── view ──────────────────────────────────────────────────────────────────────

def test_calendar_view(mock_client):
    mock_client.get.return_value = EVENT_VIEW_RESPONSE
    result = runner.invoke(app, ["calendar", "view", "ev1"])
    assert result.exit_code == 0
    assert "Team Standup" in result.output


def test_calendar_view_shows_comment(mock_client):
    mock_client.get.return_value = EVENT_VIEW_RESPONSE
    result = runner.invoke(app, ["calendar", "view", "ev1"])
    assert result.exit_code == 0
    assert "Daily sync" in result.output


# ── create ────────────────────────────────────────────────────────────────────

def test_calendar_create_with_flags(mock_client):
    mock_client.post.return_value = {"data": {"id": "new-ev"}}
    result = runner.invoke(app, [
        "calendar", "create",
        "--title", "All Hands",
        "--start", "2025-07-01 10:00:00",
        "--end", "2025-07-01 11:00:00",
    ])
    assert result.exit_code == 0
    assert "All Hands" in result.output or "created" in result.output.lower()
    payload = mock_client.post.call_args[1]["data"]
    assert payload["title"] == "All Hands"
    assert payload["start"] == "2025-07-01 10:00:00"


def test_calendar_create_with_comment(mock_client):
    mock_client.post.return_value = {"data": {"id": "new-ev2"}}
    result = runner.invoke(app, [
        "calendar", "create",
        "--title", "1:1",
        "--start", "2025-07-02 09:00:00",
        "--end", "2025-07-02 09:30:00",
        "--comment", "Monthly check-in",
    ])
    assert result.exit_code == 0
    payload = mock_client.post.call_args[1]["data"]
    assert payload["comment"] == "Monthly check-in"


# ── update ────────────────────────────────────────────────────────────────────

def test_calendar_update_with_flags(mock_client):
    mock_client.get.return_value = EVENT_VIEW_RESPONSE
    mock_client.put.return_value = {}
    result = runner.invoke(app, [
        "calendar", "update", "ev1",
        "--title", "Team Standup (Updated)",
    ])
    assert result.exit_code == 0
    assert "updated" in result.output.lower()


# ── delete ────────────────────────────────────────────────────────────────────

def test_calendar_delete_confirmed(mock_client):
    mock_client.get.return_value = EVENT_VIEW_RESPONSE
    mock_client.delete.return_value = {}
    result = runner.invoke(app, ["calendar", "delete", "ev1"], input="y\n")
    assert result.exit_code == 0
    assert "deleted" in result.output.lower()
    mock_client.delete.assert_called_once_with("v2/event/delete/ev1")


def test_calendar_delete_cancelled(mock_client):
    mock_client.get.return_value = EVENT_VIEW_RESPONSE
    result = runner.invoke(app, ["calendar", "delete", "ev1"], input="n\n")
    # typer abort → exit 1
    assert result.exit_code == 1
    mock_client.delete.assert_not_called()


# ── bare invocation ──────────────────────────────────────────────────────────

def test_calendar_bare_shows_hint():
    result = runner.invoke(app, ["calendar"])
    assert result.exit_code == 0
    assert "sub-command" in result.output
    assert "Missing command" not in result.output
