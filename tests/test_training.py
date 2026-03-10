"""Tests for `kolay training` commands."""
import pytest
from typer.testing import CliRunner
from kolay_cli.cli import app

runner = CliRunner()

TRAINING_LIST_RESPONSE = {
    "data": {
        "items": [
            {"id": "tr1", "name": "Fire Safety", "description": "Basic fire safety", "duration": 1},
            {"id": "tr2", "name": "GDPR Awareness", "description": "Data privacy", "duration": 2},
        ],
        "totalCount": 2,
    }
}

TRAINING_VIEW_RESPONSE = {
    "data": {
        "id": "tr1",
        "name": "Fire Safety",
        "description": "Basic fire safety",
        "duration": 1,
    }
}


def test_training_list(mock_client):
    mock_client.get.return_value = TRAINING_LIST_RESPONSE
    result = runner.invoke(app, ["training", "list"])
    assert result.exit_code == 0
    assert "Fire Safety" in result.output
    assert "GDPR Awareness" in result.output


def test_training_list_with_search(mock_client):
    mock_client.get.return_value = {"data": {"items": [], "totalCount": 0}}
    result = runner.invoke(app, ["training", "list", "--search", "nothing"])
    assert result.exit_code == 0
    params = mock_client.get.call_args[1]["params"]
    assert params["search"] == "nothing"


def test_training_list_empty(mock_client):
    mock_client.get.return_value = {"data": {"items": [], "totalCount": 0}}
    result = runner.invoke(app, ["training", "list"])
    assert result.exit_code == 0
    assert "No trainings found" in result.output


def test_training_view(mock_client):
    mock_client.get.return_value = TRAINING_VIEW_RESPONSE
    result = runner.invoke(app, ["training", "view", "tr1"])
    assert result.exit_code == 0
    assert "Fire Safety" in result.output


def test_training_view_not_found(mock_client):
    """When API returns empty data, command should still exit cleanly."""
    mock_client.get.return_value = {"data": {}}
    result = runner.invoke(app, ["training", "view", "badid"])
    # Exit 0 — no data means the view renders an empty panel, no error raised
    assert result.exit_code == 0


def test_training_create_with_flags(mock_client):
    mock_client.post.return_value = {"data": {"id": "new-tr"}}
    result = runner.invoke(app, [
        "training", "create",
        "--name", "Leadership",
        "--desc", "Leadership skills",
        "--duration", "3",
    ])
    assert result.exit_code == 0
    # Success message says "added to catalogue"
    assert "added" in result.output.lower() or "catalogue" in result.output.lower()
    payload = mock_client.post.call_args[1]["data"]
    assert payload["name"] == "Leadership"


def test_training_update_with_flags(mock_client):
    mock_client.get.return_value = TRAINING_VIEW_RESPONSE
    mock_client.put.return_value = {}
    result = runner.invoke(app, ["training", "update", "tr1", "--name", "Fire Safety Pro"])
    assert result.exit_code == 0
    assert "updated" in result.output.lower()


def test_training_delete_confirmed(mock_client):
    mock_client.get.return_value = TRAINING_VIEW_RESPONSE
    mock_client.delete.return_value = {}
    result = runner.invoke(app, ["training", "delete", "tr1"], input="y\n")
    assert result.exit_code == 0
    # Success message says "removed from catalogue"
    assert "removed" in result.output.lower() or "catalogue" in result.output.lower()
    mock_client.delete.assert_called_once_with("v2/training/delete/tr1")


def test_training_delete_cancelled(mock_client):
    mock_client.get.return_value = TRAINING_VIEW_RESPONSE
    result = runner.invoke(app, ["training", "delete", "tr1"], input="n\n")
    # typer.confirm with abort=True raises Abort exit code 1 in test runner
    assert result.exit_code == 1
    mock_client.delete.assert_not_called()
