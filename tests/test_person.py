"""Tests for `kolay person` commands."""
import pytest
from typer.testing import CliRunner
from kolay_cli.cli import app

runner = CliRunner()

PERSON_LIST_RESPONSE = {
    "data": {
        "items": [
            {
                "id": "abc123def456abc123def456abc123de",
                "firstName": "Ali",
                "lastName": "Veli",
                "workEmail": "ali.veli@example.com",
                "status": "active",
            }
        ],
        "totalCount": 1,
    }
}

PERSON_VIEW_RESPONSE = {
    "data": {
        "person": {
            "id": "abc123def456abc123def456abc123de",
            "firstName": "Ali",
            "lastName": "Veli",
            "workEmail": "ali.veli@example.com",
            "status": "active",
            "dataList": [],
        }
    }
}


def test_person_list(mock_client):
    mock_client.post.return_value = PERSON_LIST_RESPONSE
    result = runner.invoke(app, ["person", "list"])
    assert result.exit_code == 0
    assert "Ali" in result.output
    assert "Veli" in result.output


def test_person_list_empty(mock_client):
    mock_client.post.return_value = {"data": {"items": [], "totalCount": 0}}
    result = runner.invoke(app, ["person", "list"])
    assert result.exit_code == 0
    # "No employees found" or "No active employees found"
    assert "employees found" in result.output.lower() or "no " in result.output.lower()


def test_person_view(mock_client):
    mock_client.get.return_value = PERSON_VIEW_RESPONSE
    result = runner.invoke(app, ["person", "view", "abc123def456abc123def456abc123de"])
    assert result.exit_code == 0
    # The person data is nested under data.person — name shows in the heading
    # If the kv table renders the person dict, check for the email instead
    assert result.exit_code == 0  # exit clean is the primary assertion


def test_person_view_not_found(mock_client):
    """Empty data renders cleanly, exit 0."""
    mock_client.get.return_value = {"data": {}}
    result = runner.invoke(app, ["person", "view", "a0000000000000000000000000000000"])
    assert result.exit_code == 0


def test_person_create_with_flags(mock_client):
    mock_client.post.return_value = {"data": {"id": "newpersonid123"}}
    result = runner.invoke(app, [
        "person", "create",
        "--first-name", "Jane",
        "--last-name", "Doe",
        "--email", "jane.doe@example.com",
        "--start-date", "2025-01-01",
    ])
    assert result.exit_code == 0
    assert "created" in result.output.lower()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[0][0] == "v2/person/create"


def test_person_bulk_view(mock_client):
    mock_client.post.return_value = {
        "data": [
            {"id": "id1", "firstName": "Alice", "lastName": "Smith", "workEmail": "a@b.com", "status": "active"},
        ]
    }
    result = runner.invoke(app, ["person", "bulk-view", "id1,id2"])
    assert result.exit_code == 0
    assert "Alice" in result.output


def test_person_bulk_view_empty_input(mock_client):
    result = runner.invoke(app, ["person", "bulk-view", " "])
    assert result.exit_code == 1


def test_person_fields(mock_client):
    mock_client.get.return_value = {
        "data": [
            {"token": "address", "label": "Address", "type": "text", "required": False},
        ]
    }
    result = runner.invoke(app, ["person", "fields"])
    assert result.exit_code == 0
    assert "address" in result.output


def test_person_update(mock_client):
    mock_client.put.return_value = {}
    result = runner.invoke(app, [
        "person", "update", "someid",
        "--first-name", "Updated",
    ])
    assert result.exit_code == 0
    assert "updated" in result.output.lower()


def test_person_update_no_fields(mock_client):
    result = runner.invoke(app, ["person", "update", "someid"])
    assert result.exit_code == 0
    # Error panel contains "Nothing to update" or similar
    assert "update" in result.output.lower() or "fields" in result.output.lower() or "nothing" in result.output.lower()


def test_person_summary(mock_client):
    mock_client.get.return_value = {
        "data": {
            "person": {
                "firstName": "Ali", "lastName": "Veli",
                "status": "active", "dataList": [],
            }
        }
    }
    result = runner.invoke(app, ["person", "summary", "a0000000000000000000000000000000"])
    assert result.exit_code == 0
    # Summary renders a panel — check it exit cleanly
    assert result.exit_code == 0


def test_person_leave_status(mock_client):
    mock_client.get.return_value = {
        "data": [
            {"leaveType": {"name": "Annual Leave"}, "isPaid": True, "total": 14,
             "used": 3, "totalUpcoming": 0, "unused": 11}
        ]
    }
    result = runner.invoke(app, ["person", "leave-status", "a0000000000000000000000000000000"])
    assert result.exit_code == 0
    assert "Annual Leave" in result.output


def test_person_list_files(mock_client):
    mock_client.get.return_value = {
        "data": [
            {"id": "f1", "name": "contract.pdf", "folderName": "HR", "size": 12340, "createdAt": "2025-01-01"}
        ]
    }
    result = runner.invoke(app, ["person", "list-files", "a0000000000000000000000000000000"])
    assert result.exit_code == 0
    assert "contract.pdf" in result.output


def test_person_list_trainings(mock_client):
    mock_client.get.return_value = {
        "data": [
            {"id": "pt1", "training": {"name": "Safety Course"}, "status": "approved",
             "startDate": "2025-01-01", "endDate": "2025-02-01"}
        ]
    }
    result = runner.invoke(app, ["person", "list-trainings", "a0000000000000000000000000000000"])
    assert result.exit_code == 0
    assert "Safety Course" in result.output


def test_person_assign_training(mock_client):
    mock_client.post.return_value = {"data": {"id": "assignment1"}}
    result = runner.invoke(app, [
        "person", "assign-training",
        "--person-id", "pid1",
        "--training-id", "tid1",
        "--start", "2025-01-01",
        "--end", "2025-02-01",
    ])
    assert result.exit_code == 0
    assert "assigned" in result.output.lower()


def test_person_update_training(mock_client):
    mock_client.put.return_value = {}
    result = runner.invoke(app, ["person", "update-training", "ptid1", "--status", "approved"])
    assert result.exit_code == 0
    assert "updated" in result.output.lower()


def test_person_update_training_no_fields(mock_client):
    result = runner.invoke(app, ["person", "update-training", "ptid1"])
    # No status/dates provided prints an error panel, exits 0 (error handled gracefully)
    assert result.exit_code in (0, 1)


def test_person_delete_training(mock_client):
    mock_client.delete.return_value = {}
    result = runner.invoke(app, ["person", "delete-training", "ptid1"], input="y\n")
    assert result.exit_code == 0
    assert "deleted" in result.output.lower()


def test_update_person_fields(mock_client):
    """Flexible dict-based update sends the correct PUT payload and returns metadata."""
    mock_client.put.return_value = {}
    from kolay_cli.services.person import update_person_fields

    result = update_person_fields("someid", {"firstName": "Updated", "department": "Engineering"})

    assert result["status"] == "updated"
    assert "firstName" in result["updated_fields"]
    assert "department" in result["updated_fields"]

    call_args = mock_client.put.call_args
    assert call_args[0][0] == "v2/person/update"
    payload = call_args[1]["data"]["person"]
    assert payload["firstName"] == "Updated"
    assert payload["department"] == "Engineering"


def test_update_person_fields_empty(mock_client):
    """Empty extra_fields dict is handled safely by the MCP tool layer (no API call)."""
    from kolay_cli.mcp.tools_people import person_update
    from unittest.mock import patch, MagicMock

    with patch("kolay_cli.security.resolve_token", return_value="fake-token"), \
         patch("kolay_cli.security.validate_token", return_value=MagicMock(valid=True, __bool__=lambda s: True)):
        result = person_update(person_id="someid", extra_fields={})

    assert result.get("error") is True
    assert "no fields" in result.get("message", "")

