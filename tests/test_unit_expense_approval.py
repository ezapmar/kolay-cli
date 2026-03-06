"""Tests for `kolay unit`, `kolay expense`, and `kolay approval` commands."""
import pytest
from typer.testing import CliRunner
from kolay_cli.cli import app

runner = CliRunner()


# ── Unit ──────────────────────────────────────────────────────────────────────

UNIT_TREE_RESPONSE = {
    "data": [
        {
            "name": "Company HQ",
            "id": "unit1",
            "items": [
                {"name": "Istanbul", "id": "item1"},
                {"name": "Ankara", "id": "item2"},
            ],
            "children": [],
        }
    ]
}


def test_unit_tree(mock_client):
    mock_client.get.return_value = UNIT_TREE_RESPONSE
    result = runner.invoke(app, ["unit", "tree"])
    assert result.exit_code == 0
    assert "Company HQ" in result.output
    assert "Istanbul" in result.output


def test_unit_tree_empty(mock_client):
    mock_client.get.return_value = {"data": []}
    result = runner.invoke(app, ["unit", "tree"])
    assert result.exit_code == 0
    # Updated message: "No organisational units found."
    assert "No organisational units found" in result.output


def test_unit_create_item_with_flags(mock_client):
    """With all flags provided no tree fetch is needed — goes straight to POST."""
    mock_client.post.return_value = {"data": {"id": "new-item"}}
    result = runner.invoke(app, [
        "unit", "create-item",
        "--unit-id", "unit1",
        "--unit-name", "Location",
        "--name", "Amsterdam",
    ])
    assert result.exit_code == 0
    assert "amsterdam" in result.output.lower()
    assert "added" in result.output.lower()
    payload = mock_client.post.call_args[1]["data"]
    assert payload["unitName"] == "Location"
    assert payload["unitItemName"] == "Amsterdam"


def test_unit_tree_with_filter(mock_client):
    """--filter flattens the tree and shows only matching nodes."""
    mock_client.get.return_value = UNIT_TREE_RESPONSE
    result = runner.invoke(app, ["unit", "tree", "--filter", "Istanbul"])
    assert result.exit_code == 0
    assert "Istanbul" in result.output


def test_unit_tree_filter_no_match_shows_all(mock_client):
    """When --filter matches nothing, fall back to showing all."""
    mock_client.get.return_value = UNIT_TREE_RESPONSE
    result = runner.invoke(app, ["unit", "tree", "--filter", "zzznomatch"])
    assert result.exit_code == 0
    # Fallback renders all items
    assert "Company HQ" in result.output or "Istanbul" in result.output


# ── Expense ───────────────────────────────────────────────────────────────────

EXPENSE_CATEGORIES_RESPONSE = {
    "data": [
        {"id": "cat1", "title": "Transport", "isEnable": True, "description": "Travel costs"},
        {"id": "cat2", "title": "Meals", "isEnable": False, "description": "Food expense"},
    ]
}


def test_expense_categories(mock_client):
    mock_client.get.return_value = EXPENSE_CATEGORIES_RESPONSE
    result = runner.invoke(app, ["expense", "categories"])
    assert result.exit_code == 0
    assert "Transport" in result.output
    assert "Meals" in result.output


def test_expense_categories_with_title_filter(mock_client):
    mock_client.get.return_value = {"data": []}
    result = runner.invoke(app, ["expense", "categories", "--title", "Taksi"])
    assert result.exit_code == 0
    params = mock_client.get.call_args[1]["params"]
    assert params["title"] == "Taksi"


def test_expense_categories_enabled_filter(mock_client):
    mock_client.get.return_value = {"data": []}
    result = runner.invoke(app, ["expense", "categories", "--enabled"])
    assert result.exit_code == 0
    params = mock_client.get.call_args[1]["params"]
    assert params["isEnable"] == 1


def test_expense_categories_empty(mock_client):
    mock_client.get.return_value = {"data": []}
    result = runner.invoke(app, ["expense", "categories"])
    assert result.exit_code == 0
    assert "No expense categories found" in result.output


# ── Approval ──────────────────────────────────────────────────────────────────

APPROVAL_LIST_RESPONSE = {
    "data": [
        {"id": "ap1", "name": "Leave Approval", "type": "leave", "steps": ["step1", "step2"]},
        {"id": "ap2", "name": "Expense Approval", "type": "expense", "steps": ["step3"]},
    ]
}


def test_approval_list(mock_client):
    mock_client.get.return_value = APPROVAL_LIST_RESPONSE
    result = runner.invoke(app, ["approval", "list"])
    assert result.exit_code == 0
    assert "Leave Approval" in result.output
    assert "Expense Approval" in result.output


def test_approval_list_empty(mock_client):
    mock_client.get.return_value = {"data": []}
    result = runner.invoke(app, ["approval", "list"])
    assert result.exit_code == 0
    assert "No approval processes" in result.output


def test_approval_list_with_filter(mock_client):
    mock_client.get.return_value = APPROVAL_LIST_RESPONSE
    result = runner.invoke(app, ["approval", "list", "--filter", "Leave"])
    assert result.exit_code == 0
    assert "Leave Approval" in result.output


def test_approval_list_filter_by_type(mock_client):
    mock_client.get.return_value = APPROVAL_LIST_RESPONSE
    result = runner.invoke(app, ["approval", "list", "--filter", "expense"])
    assert result.exit_code == 0
    assert "Expense Approval" in result.output
