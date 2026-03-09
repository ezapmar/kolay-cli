"""Tests for agent-native --json and --yes flags."""
from __future__ import annotations
import json
import pytest
from typer.testing import CliRunner
from kolay_cli.cli import app
from kolay_cli.api.errors import APIError

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_output_state():
    """Reset global JSON/yes mode between tests."""
    from kolay_cli.ui.output import set_json_mode, set_yes_mode
    set_json_mode(False)
    set_yes_mode(False)
    yield
    set_json_mode(False)
    set_yes_mode(False)


# ── --json version ────────────────────────────────────────────────────────────

def test_version_json():
    result = runner.invoke(app, ["--json", "--version"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "version" in data


def test_version_human():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Kolay CLI" in result.output


# ── --json list output ────────────────────────────────────────────────────────

PERSON_LIST_RESPONSE = {
    "data": {
        "items": [
            {"id": "a0000000000000000000000000000000", "firstName": "Alice", "lastName": "Smith", "workEmail": "alice@co.com"},
            {"id": "p2", "firstName": "Bob", "lastName": "Jones", "workEmail": "bob@co.com"},
        ],
        "totalCount": 2,
    }
}


def test_person_list_json(mock_client):
    mock_client.post.return_value = PERSON_LIST_RESPONSE
    result = runner.invoke(app, ["--json", "person", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["totalCount"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["firstName"] == "Alice"


def test_person_list_json_empty(mock_client):
    """JSON mode still returns valid JSON even when empty."""
    mock_client.post.return_value = {"data": {"items": [], "totalCount": 0}}
    result = runner.invoke(app, ["--json", "person", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["items"] == []


# ── --json view output ────────────────────────────────────────────────────────

def test_person_view_json(mock_client):
    mock_client.get.return_value = {
        "data": {"id": "a0000000000000000000000000000000", "firstName": "Alice", "lastName": "Smith", "status": "active"}
    }
    result = runner.invoke(app, ["--json", "person", "view", "a0000000000000000000000000000000"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["firstName"] == "Alice"


# ── Semantic exit codes ───────────────────────────────────────────────────────

def test_api_error_exit_code_mapping():
    """APIError.exit_code maps HTTP status to semantic codes."""
    assert APIError("bad", status_code=400).exit_code == 2
    assert APIError("auth", status_code=401).exit_code == 4
    assert APIError("forbidden", status_code=403).exit_code == 4
    assert APIError("missing", status_code=404).exit_code == 3
    assert APIError("conflict", status_code=409).exit_code == 5
    assert APIError("validation", status_code=422).exit_code == 2
    assert APIError("server", status_code=500).exit_code == 1
    assert APIError("unknown", status_code=999).exit_code == 1
    assert APIError("no status").exit_code == 1


def test_api_error_to_dict():
    """to_dict() returns structured JSON-friendly error data."""
    err = APIError("Not found", status_code=404)
    d = err.to_dict()
    assert d["error"] is True
    assert d["message"] == "Not found"
    assert d["status"] == 404
    assert d["exit_code"] == 3
    # Hint should have Rich markup stripped
    assert "[" not in d.get("hint", "")


def test_json_error_output(mock_client):
    """--json mode produces structured error on API failure."""
    mock_client.post.side_effect = APIError("Token expired", status_code=401)
    result = runner.invoke(app, ["--json", "person", "list"])
    assert result.exit_code == 4  # semantic: auth
    data = json.loads(result.output)
    assert data["error"] is True
    assert data["status"] == 401


# ── --yes flag ────────────────────────────────────────────────────────────────

def test_yes_flag_bypasses_confirm(mock_client):
    """--yes should skip confirmation on delete commands."""
    mock_client.get.return_value = {
        "data": {"id": "t1", "name": "Python 101"}
    }
    mock_client.delete.return_value = {"data": {}}
    result = runner.invoke(app, ["--yes", "training", "delete", "t1"])
    assert result.exit_code == 0
    assert "removed" in result.output.lower() or "deleted" in result.output.lower()
    mock_client.delete.assert_called_once()
