"""Tests for `kolay leave` and `kolay transaction` commands."""
import pytest
from typer.testing import CliRunner
from kolay_cli.cli import app

runner = CliRunner()

# ── Leave ──────────────────────────────────────────────────────────────────────

LEAVE_LIST_RESPONSE = {
    "data": [
        {
            "id": "lv1",
            "person": {"name": "Ali Veli"},
            "leaveType": {"name": "Annual Leave"},
            "startDate": "2025-03-01 09:00:00",
            "endDate": "2025-03-05 18:00:00",
            "status": "approved",
        }
    ]
}

LEAVE_VIEW_RESPONSE = {
    "data": {
        "id": "lv1",
        "person": {"name": "Ali Veli"},
        "leaveType": {"name": "Annual Leave"},
        "startDate": "2025-03-01",
        "endDate": "2025-03-05",
        "status": "approved",
    }
}


def test_leave_list(mock_client):
    mock_client.get.return_value = LEAVE_LIST_RESPONSE
    result = runner.invoke(app, ["leave", "list"])
    assert result.exit_code == 0
    assert "Ali Veli" in result.output
    assert "Annual" in result.output  # Rich may wrap long strings


def test_leave_list_empty(mock_client):
    mock_client.get.return_value = {"data": []}
    result = runner.invoke(app, ["leave", "list"])
    assert result.exit_code == 0
    assert "No approved leave records found" in result.output


def test_leave_list_with_filters(mock_client):
    mock_client.get.return_value = {"data": []}
    result = runner.invoke(app, ["leave", "list", "--status", "waiting", "--person-id", "pid1"])
    assert result.exit_code == 0
    params = mock_client.get.call_args[1]["params"]
    assert params["status"] == "waiting"
    assert params["personId"] == "pid1"


def test_leave_list_with_name_filter(mock_client):
    mock_client.get.return_value = LEAVE_LIST_RESPONSE
    result = runner.invoke(app, ["leave", "list", "--filter", "Ali"])
    assert result.exit_code == 0
    assert "Ali Veli" in result.output


def test_leave_list_filter_no_match_shows_all(mock_client):
    """When --filter matches nothing, fall back to showing all records."""
    mock_client.get.return_value = LEAVE_LIST_RESPONSE
    result = runner.invoke(app, ["leave", "list", "--filter", "zzznomatch"])
    assert result.exit_code == 0
    # Fallback renders all items
    assert "Ali Veli" in result.output


def test_leave_view(mock_client):
    mock_client.get.return_value = LEAVE_VIEW_RESPONSE
    result = runner.invoke(app, ["leave", "view", "lv1"])
    assert result.exit_code == 0
    assert "Annual Leave" in result.output


def test_leave_view_not_found(mock_client):
    """Empty data → view renders headings, exits cleanly without error."""
    mock_client.get.return_value = {"data": {}}
    result = runner.invoke(app, ["leave", "view", "badid"])
    assert result.exit_code == 0


def test_leave_create(mock_client):
    """Leave create with all flags bypasses interactive prompts."""
    mock_client.post.return_value = {"data": {"id": "new-lv"}}
    result = runner.invoke(app, [
        "leave", "create",
        "--person-id", "pid1",
        "--type-id", "lt1",
        "--start", "2025-06-01 09:00:00",
        "--end", "2025-06-05 18:00:00",
    ])
    assert result.exit_code == 0
    assert "submitted" in result.output.lower() or "success" in result.output.lower()


# ── Transaction ────────────────────────────────────────────────────────────────

TRX_LIST_RESPONSE = {
    "data": {
        "items": [
            {
                "id": "tx1",
                "person": {"firstName": "Fatma", "lastName": "Kaya"},
                "type": "bonus",
                "amount": 5000,
                "currency": "TL",
                "date": "2025-01-15",
                "status": "approved",
            }
        ],
        "totalCount": 1,
    }
}

TRX_VIEW_RESPONSE = {
    "data": {
        "id": "tx1",
        "type": "bonus",
        "amount": 5000,
        "currency": "TL",
        "date": "2025-01-15",
        "status": "approved",
        "items": [],
    }
}


def test_transaction_list(mock_client):
    mock_client.post.return_value = TRX_LIST_RESPONSE
    result = runner.invoke(app, ["transaction", "list"])
    assert result.exit_code == 0
    assert "Fatma" in result.output
    assert "bonus" in result.output


def test_transaction_list_empty(mock_client):
    mock_client.post.return_value = {"data": {"items": [], "totalCount": 0}}
    result = runner.invoke(app, ["transaction", "list"])
    assert result.exit_code == 0
    assert "No transactions found" in result.output


def test_transaction_list_with_filter(mock_client):
    mock_client.post.return_value = TRX_LIST_RESPONSE
    result = runner.invoke(app, ["transaction", "list", "--filter", "Fatma"])
    assert result.exit_code == 0
    assert "Fatma" in result.output


def test_transaction_list_filter_by_type(mock_client):
    mock_client.post.return_value = TRX_LIST_RESPONSE
    result = runner.invoke(app, ["transaction", "list", "--filter", "bonus"])
    assert result.exit_code == 0
    assert "bonus" in result.output


def test_transaction_view(mock_client):
    mock_client.get.return_value = TRX_VIEW_RESPONSE
    result = runner.invoke(app, ["transaction", "view", "tx1"])
    assert result.exit_code == 0
    assert "bonus" in result.output


def test_transaction_create(mock_client):
    mock_client.post.return_value = {}
    result = runner.invoke(app, [
        "transaction", "create",
        "--person-id", "pid1",
        "--type", "bonus",
        "--amount", "1000",
        "--currency", "TL",
        "--date", "2025-01-15",
    ])
    assert result.exit_code == 0
    # Success message says "created successfully"
    assert "created" in result.output.lower() or "success" in result.output.lower()


def test_transaction_delete_confirmed(mock_client):
    mock_client.delete.return_value = {}
    result = runner.invoke(app, ["transaction", "delete", "tx1"], input="y\n")
    assert result.exit_code == 0
    assert "deleted" in result.output.lower()


def test_transaction_delete_cancelled(mock_client):
    result = runner.invoke(app, ["transaction", "delete", "tx1"], input="n\n")
    # typer.confirm abort=True → exit code 1 in test runner
    assert result.exit_code == 1
    mock_client.delete.assert_not_called()
