"""
tests/test_coverage_boost.py — Targeted tests to raise < 70% coverage modules.

Targets:
  - commands/schema.py        (was 25%)  → _opt_entry, _walk, export_schema, _get_version
  - commands/unit.py          (was 62%)  → create-item interactive + flags, json mode
  - commands/person.py        (was 64%)  → terminate, update, create, bulk-view, fields,
                                           rehire, list-files, delete-file, delete-folder,
                                           leave-status, summary, assign-training,
                                           update-training, delete-training, upload-file errors
  - ui/output.py              (was 67%)  → resolve_row (invalid row, over range), require_arg,
                                           json_output with stderr_msg, json_error with hints,
                                           KOLAY_OUTPUT=json env var, is_yes_mode
  - ui/pickers.py             (was 8%)   → module imports without crashing (structural only;
                                           TTY-dependent internals skip gracefully)
"""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from kolay_cli.cli import app

runner = CliRunner()


# ══════════════════════════════════════════════════════════════════════════════
# 1. commands/schema.py
# ══════════════════════════════════════════════════════════════════════════════

class TestSchema:
    def test_schema_command_exits_zero(self):
        result = runner.invoke(app, ["schema"])
        assert result.exit_code == 0

    def test_schema_output_is_valid_json(self):
        result = runner.invoke(app, ["schema"])
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_schema_contains_name_and_version(self):
        result = runner.invoke(app, ["schema"])
        data = json.loads(result.output)
        assert data["name"] == "kolay"
        assert "version" in data

    def test_schema_contains_commands_key(self):
        result = runner.invoke(app, ["schema"])
        data = json.loads(result.output)
        assert "commands" in data
        assert isinstance(data["commands"], dict)

    def test_schema_lists_person_command(self):
        result = runner.invoke(app, ["schema"])
        data = json.loads(result.output)
        assert "person" in data["commands"]

    def test_schema_lists_mcp_command(self):
        result = runner.invoke(app, ["schema"])
        data = json.loads(result.output)
        assert "mcp" in data["commands"]

    def test_schema_does_not_self_reference(self):
        """schema must pop itself from the output tree."""
        result = runner.invoke(app, ["schema"])
        data = json.loads(result.output)
        assert "schema" not in data["commands"]

    def test_schema_version_matches_package(self):
        from kolay_cli import __version__
        result = runner.invoke(app, ["schema"])
        data = json.loads(result.output)
        assert data["version"] == __version__

    def test_opt_entry_omits_sensitive_defaults(self):
        """_opt_entry must not include defaults for token/password/url options."""
        import click
        from kolay_cli.commands.schema import _opt_entry
        opt = click.Option(["--api-token"], default="my-secret", type=click.STRING, help="Token")
        entry = _opt_entry(opt)
        assert "default" not in entry

    def test_opt_entry_includes_nonsensitive_defaults(self):
        import click
        from kolay_cli.commands.schema import _opt_entry
        opt = click.Option(["--limit"], default=20, type=click.INT, help="Limit results")
        entry = _opt_entry(opt)
        assert entry["default"] == 20

    def test_opt_entry_includes_required_flag(self):
        import click
        from kolay_cli.commands.schema import _opt_entry
        opt = click.Option(["--name"], required=True, type=click.STRING)
        entry = _opt_entry(opt)
        assert entry["required"] is True

    def test_get_version_returns_string(self):
        from kolay_cli.commands.schema import _get_version
        v = _get_version()
        assert isinstance(v, str)
        assert len(v) > 0

    def test_schema_help_shows_up_in_help(self):
        result = runner.invoke(app, ["--help"])
        # schema is hidden=True — should not appear in public help
        # This just verifies --help still works cleanly
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
# 2. commands/unit.py — uncovered branches
# ══════════════════════════════════════════════════════════════════════════════

UNIT_TREE_DATA = [
    {
        "id": "u1", "name": "Engineering",
        "items": [{"id": "i1", "name": "Backend"}],
        "children": [{"id": "u2", "name": "Frontend", "items": [], "children": []}],
    }
]

class TestUnitExtended:
    def test_unit_tree_json_mode(self, mock_client):
        mock_client.get.return_value = {"data": UNIT_TREE_DATA}
        result = runner.invoke(app, ["--json", "unit", "tree"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_unit_tree_renders_nested_children(self, mock_client):
        mock_client.get.return_value = {"data": UNIT_TREE_DATA}
        result = runner.invoke(app, ["unit", "tree"])
        assert result.exit_code == 0
        assert "Engineering" in result.output
        assert "Frontend" in result.output

    def test_unit_tree_renders_items(self, mock_client):
        mock_client.get.return_value = {"data": UNIT_TREE_DATA}
        result = runner.invoke(app, ["unit", "tree"])
        assert "Backend" in result.output

    def test_unit_create_item_interactive_picker_and_name(self, mock_client):
        """Interactive path: no flags → shows picker, prompts for unit/name."""
        mock_client.get.return_value = {"data": UNIT_TREE_DATA}
        mock_client.post.return_value = {"data": {"id": "new1"}}
        result = runner.invoke(
            app, ["unit", "create-item"],
            input="1\nLocation\nAmsterdam\n",
        )
        assert result.exit_code == 0
        assert "Amsterdam" in result.output or "added" in result.output.lower()

    def test_unit_create_item_with_all_flags(self, mock_client):
        mock_client.post.return_value = {"data": {"id": "new2"}}
        result = runner.invoke(app, [
            "unit", "create-item",
            "--unit-id", "u1",
            "--unit-name", "Location",
            "--name", "Berlin",
        ])
        assert result.exit_code == 0
        assert "Berlin" in result.output or "added" in result.output.lower()

    def test_unit_create_item_empty_tree_shows_error(self, mock_client):
        """If tree is empty, show a human error (not a crash)."""
        mock_client.get.return_value = {"data": []}
        result = runner.invoke(app, ["unit", "create-item"])
        assert result.exit_code == 0
        assert "No organisational units" in result.output or "error" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════════
# 3. commands/person.py — uncovered commands
# ══════════════════════════════════════════════════════════════════════════════

PERSON_DATA = {"id": "a0000000000000000000000000000000", "firstName": "Alice", "lastName": "Smith", "status": "active", "workEmail": "a@co.com"}
PERSON_LIST = {"data": {"items": [PERSON_DATA], "totalCount": 1}}


class TestPersonExtended:

    # ── terminate ─────────────────────────────────────────────────────────────

    def test_terminate_with_flags_and_yes(self, mock_client):
        mock_client.get.return_value = {"data": PERSON_DATA}
        mock_client.post.return_value = {"data": {}}
        result = runner.invoke(app, [
            "--yes", "person", "terminate", "a0000000000000000000000000000000",
            "--termination-date", "2026-03-08",
            "--reason", "01",
        ])
        assert result.exit_code == 0
        assert "terminated" in result.output.lower() or "success" in result.output.lower()

    def test_terminate_json_mode_with_flags(self, mock_client):
        mock_client.get.return_value = {"data": PERSON_DATA}
        mock_client.post.return_value = {"data": {"terminated": True}}
        result = runner.invoke(app, [
            "--json", "--yes", "person", "terminate", "a0000000000000000000000000000000",
            "--termination-date", "2026-03-08",
            "--reason", "01",
        ])
        assert result.exit_code == 0

    def test_terminate_json_missing_person_id_exits_2(self, mock_client):
        """In --json mode, omitting person-id should exit 2 not prompt."""
        result = runner.invoke(app, ["--json", "person", "terminate"])
        assert result.exit_code == 2

    # ── update ────────────────────────────────────────────────────────────────

    def test_update_first_name(self, mock_client):
        mock_client.put.return_value = {"data": {}}
        result = runner.invoke(app, ["person", "update", "a0000000000000000000000000000000", "--first-name", "Bob"])
        assert result.exit_code == 0
        assert "updated" in result.output.lower() or "success" in result.output.lower()

    def test_update_nothing_to_update_exits_cleanly(self, mock_client):
        result = runner.invoke(app, ["person", "update", "a0000000000000000000000000000000"])
        assert result.exit_code == 0
        assert "nothing to update" in result.output.lower()

    def test_update_custom_field(self, mock_client):
        mock_client.put.return_value = {"data": {}}
        result = runner.invoke(app, ["person", "update", "a0000000000000000000000000000000", "--custom", "adres=Street 1"])
        assert result.exit_code == 0

    def test_update_json_mode(self, mock_client):
        mock_client.put.return_value = {"data": {"id": "a0000000000000000000000000000000"}}
        result = runner.invoke(app, ["--json", "person", "update", "a0000000000000000000000000000000", "--email", "new@co.com"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "person_id" in data or "status" in data

    # ── summary ───────────────────────────────────────────────────────────────

    def test_summary_basic(self, mock_client):
        mock_client.get.return_value = {"data": {"firstName": "Alice", "lastName": "Smith", "dataList": []}}
        result = runner.invoke(app, ["person", "summary", "a0000000000000000000000000000000"])
        assert result.exit_code == 0
        assert "Alice" in result.output

    def test_summary_with_custom_fields(self, mock_client):
        mock_client.get.return_value = {"data": {
            "firstName": "Alice", "lastName": "Smith",
            "dataList": [{"fieldToken": "adres", "value": "Straße 1"}],
        }}
        result = runner.invoke(app, ["person", "summary", "a0000000000000000000000000000000"])
        assert result.exit_code == 0
        assert "Custom Fields" in result.output or "adres" in result.output

    # ── create ────────────────────────────────────────────────────────────────

    def test_create_with_all_flags(self, mock_client):
        mock_client.post.return_value = {"data": {"id": "new123"}}
        result = runner.invoke(app, [
            "person", "create",
            "--first-name", "New", "--last-name", "Employee",
            "--email", "new@co.com", "--start-date", "2026-03-08",
        ])
        assert result.exit_code == 0
        assert "new123" in result.output or "created" in result.output.lower()

    def test_create_interactive_prompts(self, mock_client):
        mock_client.post.return_value = {"data": {"id": "new456"}}
        result = runner.invoke(app, ["person", "create"], input="Alice\nWonder\nalice@co.com\n2026-01-01\n")
        assert result.exit_code == 0

    # ── bulk-view ─────────────────────────────────────────────────────────────

    def test_bulk_view_with_ids(self, mock_client):
        mock_client.post.return_value = {"data": [PERSON_DATA]}
        result = runner.invoke(app, ["person", "bulk-view", "p1,p2"])
        assert result.exit_code == 0
        assert "Alice" in result.output

    def test_bulk_view_empty_returns_empty_message(self, mock_client):
        mock_client.post.return_value = {"data": []}
        result = runner.invoke(app, ["person", "bulk-view", "a0000000000000000000000000000000"])
        assert result.exit_code == 0
        assert "no" in result.output.lower() or "empty" in result.output.lower()

    # ── fields ────────────────────────────────────────────────────────────────

    def test_fields_shows_table(self, mock_client):
        mock_client.get.return_value = {"data": [
            {"token": "adres", "label": "Address", "type": "text", "required": False}
        ]}
        result = runner.invoke(app, ["person", "fields"])
        assert result.exit_code == 0
        assert "adres" in result.output

    def test_fields_empty_shows_message(self, mock_client):
        mock_client.get.return_value = {"data": []}
        result = runner.invoke(app, ["person", "fields"])
        assert result.exit_code == 0

    # ── rehire ────────────────────────────────────────────────────────────────

    def test_rehire_with_flags(self, mock_client):
        mock_client.post.return_value = {"data": {}}
        result = runner.invoke(app, ["person", "rehire", "a0000000000000000000000000000000", "--start-date", "2026-06-01"])
        assert result.exit_code == 0
        assert "rehired" in result.output.lower() or "success" in result.output.lower()

    # ── list-files ────────────────────────────────────────────────────────────

    def test_list_files(self, mock_client):
        mock_client.get.return_value = {"data": [
            {"id": "f1", "name": "contract.pdf", "folderName": "HR Documents"}
        ]}
        result = runner.invoke(app, ["person", "list-files", "a0000000000000000000000000000000"])
        assert result.exit_code == 0
        assert "contract.pdf" in result.output

    def test_list_files_empty(self, mock_client):
        mock_client.get.return_value = {"data": []}
        result = runner.invoke(app, ["person", "list-files", "a0000000000000000000000000000000"])
        assert result.exit_code == 0

    # ── delete-file ───────────────────────────────────────────────────────────

    def test_delete_file_with_yes(self, mock_client):
        mock_client.delete.return_value = {"data": {}}
        result = runner.invoke(app, ["--yes", "person", "delete-file", "f1"])
        assert result.exit_code == 0

    # ── delete-folder ─────────────────────────────────────────────────────────

    def test_delete_folder_with_yes(self, mock_client):
        mock_client.delete.return_value = {"data": {}}
        result = runner.invoke(app, ["--yes", "person", "delete-folder", "folder1"])
        assert result.exit_code == 0

    # ── upload-file error paths ───────────────────────────────────────────────

    def test_upload_file_not_found_exits_1(self, mock_client):
        result = runner.invoke(app, [
            "person", "upload-file",
            "--person-id", "a0000000000000000000000000000000",
            "--file", "/nonexistent/path/file.pdf",
        ])
        assert result.exit_code == 1
        assert "File not found" in result.output or "not found" in result.output.lower()

    # ── leave-status ──────────────────────────────────────────────────────────

    def test_leave_status(self, mock_client):
        mock_client.get.return_value = {"data": [
            {"leaveType": {"name": "Annual"}, "dayLimit": 20, "used": 5, "totalUpcoming": 2, "unused": 13}
        ]}
        result = runner.invoke(app, ["person", "leave-status", "a0000000000000000000000000000000"])
        assert result.exit_code == 0
        assert "Annual" in result.output

    def test_leave_status_empty(self, mock_client):
        mock_client.get.return_value = {"data": []}
        result = runner.invoke(app, ["person", "leave-status", "a0000000000000000000000000000000"])
        assert result.exit_code == 0

    def test_leave_status_json_mode(self, mock_client):
        mock_client.get.return_value = {"data": [{"leaveType": {"name": "Annual"}, "dayLimit": 20}]}
        result = runner.invoke(app, ["--json", "person", "leave-status", "a0000000000000000000000000000000"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)

    # ── person training management ────────────────────────────────────────────

    def test_list_trainings(self, mock_client):
        mock_client.get.return_value = {"data": [
            {"id": "pt1", "training": {"name": "Python 101"}, "status": "approved",
             "startDate": "2026-01-01", "endDate": "2026-02-01"}
        ]}
        result = runner.invoke(app, ["person", "list-trainings", "a0000000000000000000000000000000"])
        assert result.exit_code == 0
        assert "Python 101" in result.output

    def test_list_trainings_empty(self, mock_client):
        mock_client.get.return_value = {"data": []}
        result = runner.invoke(app, ["person", "list-trainings", "a0000000000000000000000000000000"])
        assert result.exit_code == 0

    def test_assign_training_with_flags(self, mock_client):
        mock_client.post.return_value = {"data": {"id": "pt_new"}}
        result = runner.invoke(app, [
            "person", "assign-training",
            "--person-id", "a0000000000000000000000000000000", "--training-id", "t1",
            "--start", "2026-04-01", "--end", "2026-05-01",
        ])
        assert result.exit_code == 0
        assert "assigned" in result.output.lower() or "success" in result.output.lower()

    def test_update_training_with_status(self, mock_client):
        mock_client.put.return_value = {"data": {}}
        result = runner.invoke(app, ["person", "update-training", "pt1", "--status", "approved"])
        assert result.exit_code == 0

    def test_update_training_nothing_to_update(self, mock_client):
        result = runner.invoke(app, ["person", "update-training", "pt1"])
        assert result.exit_code == 0
        assert "no fields" in result.output.lower()

    def test_delete_training_with_yes(self, mock_client):
        mock_client.delete.return_value = {"data": {}}
        result = runner.invoke(app, ["--yes", "person", "delete-training", "pt1"])
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
# 4. ui/output.py — uncovered branches
# ══════════════════════════════════════════════════════════════════════════════

class TestOutputModule:

    # ── resolve_row ───────────────────────────────────────────────────────────

    def test_resolve_row_passes_uuid_through(self):
        from kolay_cli.ui.output import resolve_row
        items = [{"id": "abc"}, {"id": "def"}]
        assert resolve_row("abc", items) == "abc"

    def test_resolve_row_valid_row_number(self):
        from kolay_cli.ui.output import resolve_row
        items = [{"id": "first"}, {"id": "second"}]
        assert resolve_row("1", items) == "first"
        assert resolve_row("2", items) == "second"

    def test_resolve_row_zero_exits_2(self):
        from kolay_cli.ui.output import resolve_row
        import click
        items = [{"id": "x"}]
        with pytest.raises(click.exceptions.Exit) as exc:
            resolve_row("0", items)
        assert exc.value.exit_code == 2

    def test_resolve_row_over_range_exits_3(self):
        from kolay_cli.ui.output import resolve_row
        import click
        items = [{"id": "x"}]
        with pytest.raises(click.exceptions.Exit) as exc:
            resolve_row("99", items)
        assert exc.value.exit_code == 3

    def test_resolve_row_custom_id_key(self):
        from kolay_cli.ui.output import resolve_row
        items = [{"personId": "p42"}]
        result = resolve_row("1", items, id_key="personId")
        assert result == "p42"

    # ── require_arg ───────────────────────────────────────────────────────────

    def test_require_arg_in_json_mode_none_exits_2(self):
        from kolay_cli.ui.output import set_json_mode, require_arg
        import click
        set_json_mode(True)
        with pytest.raises(click.exceptions.Exit) as exc:
            require_arg(None, "person-id")
        assert exc.value.exit_code == 2

    def test_require_arg_in_json_mode_with_value_does_nothing(self):
        from kolay_cli.ui.output import set_json_mode, require_arg
        set_json_mode(True)
        require_arg("a0000000000000000000000000000000", "person-id")  # must not raise

    def test_require_arg_outside_json_mode_none_does_nothing(self):
        from kolay_cli.ui.output import set_json_mode, require_arg
        set_json_mode(False)
        require_arg(None, "person-id")  # must not raise

    # ── json_output ───────────────────────────────────────────────────────────

    def test_json_output_stderr_msg(self, capsys):
        from kolay_cli.ui.output import json_output
        json_output({"key": "val"}, stderr_msg="Processing...")
        captured = capsys.readouterr()
        assert "Processing..." in captured.err
        assert json.loads(captured.out)["key"] == "val"

    # ── json_error ────────────────────────────────────────────────────────────

    def test_json_error_with_status_and_hint(self, capsys):
        from kolay_cli.ui.output import json_error
        json_error("Not found", status=404, hint="[bold]Check the ID[/bold]", exit_code=3)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"] is True
        assert data["status"] == 404
        assert data["exit_code"] == 3
        # Rich markup stripped from hint
        assert "[bold]" not in data["hint"]

    def test_json_error_minimal(self, capsys):
        from kolay_cli.ui.output import json_error
        json_error("Something went wrong")
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["message"] == "Something went wrong"
        assert data["exit_code"] == 1

    # ── KOLAY_OUTPUT=json env var ─────────────────────────────────────────────

    def test_kolay_output_env_var_activates_json_mode(self, monkeypatch):
        from kolay_cli.ui.output import set_json_mode, is_json_mode
        set_json_mode(False)
        monkeypatch.setenv("KOLAY_OUTPUT", "json")
        assert is_json_mode() is True

    def test_kolay_output_env_var_case_insensitive(self, monkeypatch):
        from kolay_cli.ui.output import set_json_mode, is_json_mode
        set_json_mode(False)
        monkeypatch.setenv("KOLAY_OUTPUT", "JSON")
        assert is_json_mode() is True

    # ── is_yes_mode ───────────────────────────────────────────────────────────

    def test_is_yes_mode_default_false(self):
        from kolay_cli.ui.output import set_yes_mode, is_yes_mode
        set_yes_mode(False)
        assert is_yes_mode() is False

    def test_is_yes_mode_true_after_set(self):
        from kolay_cli.ui.output import set_yes_mode, is_yes_mode
        set_yes_mode(True)
        assert is_yes_mode() is True


# ══════════════════════════════════════════════════════════════════════════════
# 5. ui/pickers.py — structural coverage (import + public API existence)
# ══════════════════════════════════════════════════════════════════════════════

class TestPickersModule:
    def test_pickers_module_importable(self):
        """Importing pickers must not crash — no TTY required."""
        import kolay_cli.ui.pickers as pickers_mod
        assert pickers_mod is not None

    def test_pick_person_function_exists(self):
        from kolay_cli.ui.pickers import pick_person
        assert callable(pick_person)

    def test_pick_training_function_exists(self):
        from kolay_cli.ui.pickers import pick_training
        assert callable(pick_training)

    def test_pick_person_training_function_exists(self):
        from kolay_cli.ui.pickers import pick_person_training
        assert callable(pick_person_training)

    def test_pick_person_file_function_exists(self):
        from kolay_cli.ui.pickers import pick_person_file
        assert callable(pick_person_file)

    def test_pickers_are_exported_from_ui_package(self):
        """Public pickers must be accessible via kolay_cli.ui.*"""
        from kolay_cli.ui import pick_person, pick_training
        assert callable(pick_person)
        assert callable(pick_training)
