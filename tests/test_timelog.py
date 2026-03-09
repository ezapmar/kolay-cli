"""Tests for `kolay timelog` commands."""
import pytest
from typer.testing import CliRunner
from kolay_cli.cli import app

runner = CliRunner()

TIMELOG_LIST_RESPONSE = {
    "data": {
        "items": [
            {
                "id": "tl1",
                "person": {"firstName": "Ali", "lastName": "Veli"},
                "type": "work",
                "startDate": "2025-01-10 09:00:00",
                "endDate": "2025-01-10 18:00:00",
                "description": "Daily work",
                "status": "approved",
            }
        ],
        "totalCount": 1,
    }
}

TIMELOG_VIEW_RESPONSE = {
    "data": {
        "id": "tl1",
        "type": "work",
        "status": "approved",
        "startDate": "2025-01-10 09:00:00",
        "endDate": "2025-01-10 18:00:00",
        "description": "Daily work",
        "person": {"firstName": "Ali", "lastName": "Veli"},
    }
}


def test_timelog_list(mock_client):
    mock_client.post.return_value = TIMELOG_LIST_RESPONSE
    result = runner.invoke(app, ["timelog", "list"])
    assert result.exit_code == 0
    assert "Ali" in result.output
    assert "work" in result.output


def test_timelog_list_with_filters(mock_client):
    mock_client.post.return_value = {"data": {"items": [], "totalCount": 0}}
    result = runner.invoke(app, ["timelog", "list", "--type", "overtime", "--status", "waiting"])
    assert result.exit_code == 0
    payload = mock_client.post.call_args[1]["data"]
    assert payload["type"] == "overtime"
    assert payload["status"] == "waiting"


def test_timelog_list_empty(mock_client):
    mock_client.post.return_value = {"data": {"items": [], "totalCount": 0}}
    result = runner.invoke(app, ["timelog", "list"])
    assert result.exit_code == 0
    assert "No timelog records found" in result.output


def test_timelog_list_with_name_filter(mock_client):
    mock_client.post.return_value = TIMELOG_LIST_RESPONSE
    result = runner.invoke(app, ["timelog", "list", "--filter", "Ali"])
    assert result.exit_code == 0
    assert "Ali" in result.output


def test_timelog_list_filter_by_type(mock_client):
    mock_client.post.return_value = TIMELOG_LIST_RESPONSE
    result = runner.invoke(app, ["timelog", "list", "--filter", "work"])
    assert result.exit_code == 0
    assert "work" in result.output



def test_timelog_view(mock_client):
    mock_client.get.return_value = TIMELOG_VIEW_RESPONSE
    result = runner.invoke(app, ["timelog", "view", "tl1"])
    assert result.exit_code == 0
    assert "work" in result.output


def test_timelog_view_not_found(mock_client):
    """Empty data dict → view renders heading with blank name, exit 0."""
    mock_client.get.return_value = {"data": {}}
    result = runner.invoke(app, ["timelog", "view", "nonexistent"])
    assert result.exit_code == 0


def test_timelog_create(mock_client):
    mock_client.post.return_value = {"data": {"id": "new-tl-id"}}
    result = runner.invoke(app, [
        "timelog", "create",
        "--person-id", "pid1",
        "--type", "overtime",
        "--start", "2025-01-10 09:00:00",
        "--end", "2025-01-10 12:00:00",
        "--desc", "Extra work",
    ])
    assert result.exit_code == 0
    # Success message says "submitted for approval"
    assert "submitted" in result.output.lower() or "approval" in result.output.lower()
    payload = mock_client.post.call_args[1]["data"]
    assert payload["personId"] == "pid1"
    assert payload["type"] == "overtime"


def test_timelog_delete_confirmed(mock_client):
    mock_client.delete.return_value = {}
    result = runner.invoke(app, ["timelog", "delete", "tl1"], input="y\n")
    assert result.exit_code == 0
    assert "deleted" in result.output.lower()
    mock_client.delete.assert_called_once_with("v2/timelog/delete/tl1")


def test_timelog_delete_cancelled(mock_client):
    result = runner.invoke(app, ["timelog", "delete", "tl1"], input="n\n")
    # typer.confirm abort=True raises Abort → exit 1 in test runner
    assert result.exit_code == 1
    mock_client.delete.assert_not_called()


def test_timelog_create_invalid_datetime(mock_client):
    result = runner.invoke(app, [
        "timelog", "create",
        "--person-id", "pid1",
        "--start", "invalid-date",
        "--end", "2025-01-10 12:00:00"
    ])
    assert result.exit_code == 2  # semantic: bad input
    assert "Invalid date" in result.output
    mock_client.post.assert_not_called()
