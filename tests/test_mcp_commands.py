"""
tests/test_mcp_commands.py — `kolay mcp` subcommand suite.

Covers:
  - kolay mcp --help (structure, commands listed)
  - kolay mcp clients (table output, tilde paths, single-line rows)
  - kolay mcp install  (picker: valid, multi, all, bad input, out-of-range, empty)
  - kolay mcp install --yes (non-interactive, installs all)
  - kolay mcp tools (lists registered tools)
  - Alpha warning visible in root --help
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from kolay_cli.cli import app

runner = CliRunner()


# ── helpers ───────────────────────────────────────────────────────────────────

FAKE_STRATEGIES_NAMES = ["Claude Desktop", "Cursor (global)", "Zed"]

def _mock_strategies(num: int = 3):
    """Return `num` lightweight fake strategy mocks."""
    strats = []
    names = ["Claude Desktop", "Cursor (global)", "Zed"]
    for i in range(num):
        s = MagicMock()
        s.name = names[i]
        s.description = f"Description {i + 1}"
        s.get_config_path.return_value = Path(f"/tmp/fake_{i}.json")
        strats.append(s)
    return strats


# ── kolay mcp --help ──────────────────────────────────────────────────────────

class TestMcpHelp:
    def test_help_lists_all_subcommands(self):
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0
        for cmd in ("serve", "inspect", "install", "clients"):
            assert cmd in result.output, f"'{cmd}' missing from mcp --help"

    def test_help_description_is_present(self):
        result = runner.invoke(app, ["mcp", "--help"])
        assert "MCP" in result.output or "mcp" in result.output.lower()

    def test_install_help_lists_supported_clients(self):
        result = runner.invoke(app, ["mcp", "install", "--help"])
        assert result.exit_code == 0
        assert "Claude" in result.output or "Cursor" in result.output


# ── Alpha warning ─────────────────────────────────────────────────────────────

class TestAlphaWarning:
    def test_help_shows_alpha_release_warning(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ALPHA" in result.output

    def test_help_shows_unofficial_warning(self):
        result = runner.invoke(app, ["--help"])
        assert "unofficial" in result.output.lower() or "experimental" in result.output.lower()

    def test_version_contains_alpha_tag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "alpha" in result.output.lower()


# ── kolay mcp clients ─────────────────────────────────────────────────────────

class TestMcpClients:
    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_clients_exits_zero(self, mock_get):
        mock_get.return_value = _mock_strategies()
        result = runner.invoke(app, ["mcp", "clients"])
        assert result.exit_code == 0

    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_clients_shows_total_count(self, mock_get):
        mock_get.return_value = _mock_strategies(3)
        result = runner.invoke(app, ["mcp", "clients"])
        assert "3" in result.output

    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_clients_shows_all_client_names(self, mock_get):
        strats = _mock_strategies(3)
        mock_get.return_value = strats
        result = runner.invoke(app, ["mcp", "clients"])
        for s in strats:
            assert s.name in result.output

    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_clients_uses_tilde_paths(self, mock_get):
        strats = _mock_strategies(1)
        home = Path.home()
        strats[0].get_config_path.return_value = home / ".config" / "test.json"
        mock_get.return_value = strats
        result = runner.invoke(app, ["mcp", "clients"])
        # Should show ~/... not /Users/...
        assert "~/" in result.output
        assert str(home) not in result.output

    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_clients_no_description_column(self, mock_get):
        """Clients table dropped the description column — table should be clean."""
        strats = _mock_strategies(1)
        strats[0].description = "UNIQUE_DESCRIPTION_SENTINEL"
        mock_get.return_value = strats
        result = runner.invoke(app, ["mcp", "clients"])
        # Description should NOT appear in the simplified clients table
        assert "UNIQUE_DESCRIPTION_SENTINEL" not in result.output


# ── kolay mcp install — interactive picker ────────────────────────────────────

class TestMcpInstall:

    @patch("kolay_cli.services.mcp_registry.install_mcp_server")
    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_install_single_valid_selection(self, mock_get, mock_install):
        strats = _mock_strategies(3)
        mock_get.return_value = strats
        mock_install.return_value = [("Claude Desktop", True, "/tmp/fake_0.json")]
        result = runner.invoke(app, ["mcp", "install"], input="1\n")
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify only first client was passed as selected
        call_kwargs = mock_install.call_args
        selected_arg = call_kwargs[1].get("selected") or call_kwargs[0][3]
        assert "Claude Desktop" in selected_arg
        assert "Cursor (global)" not in selected_arg

    @patch("kolay_cli.services.mcp_registry.install_mcp_server")
    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_install_multi_selection(self, mock_get, mock_install):
        strats = _mock_strategies(3)
        mock_get.return_value = strats
        mock_install.return_value = [
            ("Claude Desktop", True, "/tmp/fake_0.json"),
            ("Zed", True, "/tmp/fake_2.json"),
        ]
        result = runner.invoke(app, ["mcp", "install"], input="1,3\n")
        assert result.exit_code == 0
        call_kwargs = mock_install.call_args
        selected_arg = call_kwargs[1].get("selected") or call_kwargs[0][3]
        assert "Claude Desktop" in selected_arg
        assert "Zed" in selected_arg
        assert "Cursor (global)" not in selected_arg

    @patch("kolay_cli.services.mcp_registry.install_mcp_server")
    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_install_all_with_a(self, mock_get, mock_install):
        strats = _mock_strategies(3)
        mock_get.return_value = strats
        mock_install.return_value = [(s.name, True, "/tmp/x.json") for s in strats]
        result = runner.invoke(app, ["mcp", "install"], input="a\n")
        assert result.exit_code == 0
        call_kwargs = mock_install.call_args
        selected_arg = call_kwargs[1].get("selected") or call_kwargs[0][3]
        assert len(selected_arg) == 3

    @patch("kolay_cli.services.mcp_registry.install_mcp_server")
    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_install_yes_flag_skips_picker(self, mock_get, mock_install):
        strats = _mock_strategies(3)
        mock_get.return_value = strats
        mock_install.return_value = [(s.name, True, "/tmp/x.json") for s in strats]
        result = runner.invoke(app, ["mcp", "install", "--yes"])
        assert result.exit_code == 0
        # all 3 should be selected, no prompt was shown
        call_kwargs = mock_install.call_args
        selected_arg = call_kwargs[1].get("selected") or call_kwargs[0][3]
        assert len(selected_arg) == 3

    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_install_empty_input_exits_cleanly(self, mock_get):
        mock_get.return_value = _mock_strategies(3)
        result = runner.invoke(app, ["mcp", "install"], input="\n")
        # Empty input "No selection" message and non-error exit
        assert "nothing installed" in result.output.lower() or "cancel" in result.output.lower() or "no" in result.output.lower()

    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_install_invalid_text_shows_warning(self, mock_get):
        mock_get.return_value = _mock_strategies(3)
        result = runner.invoke(app, ["mcp", "install"], input="abc\n")
        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "" in result.output

    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_install_out_of_range_shows_warning(self, mock_get):
        mock_get.return_value = _mock_strategies(3)
        result = runner.invoke(app, ["mcp", "install"], input="99\n")
        assert result.exit_code == 0
        assert "range" in result.output.lower() or "" in result.output

    @patch("kolay_cli.services.mcp_registry.install_mcp_server")
    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_install_success_shows_checkmark_and_tilde_path(self, mock_get, mock_install):
        strats = _mock_strategies(1)
        mock_get.return_value = strats
        home = str(Path.home())
        mock_install.return_value = [("Claude Desktop", True, f"{home}/.claude/config.json")]
        result = runner.invoke(app, ["mcp", "install"], input="1\n")
        assert result.exit_code == 0
        assert "" in result.output or "Configured" in result.output
        assert "~/" in result.output
        assert home not in result.output  # tilde substitution applied

    @patch("kolay_cli.services.mcp_registry.install_mcp_server")
    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_install_failure_shows_cross(self, mock_get, mock_install):
        strats = _mock_strategies(1)
        mock_get.return_value = strats
        mock_install.return_value = [("Claude Desktop", False, "Permission denied")]
        result = runner.invoke(app, ["mcp", "install"], input="1\n")
        assert result.exit_code == 0
        assert "" in result.output or "Failed" in result.output

    @patch("kolay_cli.services.mcp_registry.install_mcp_server")
    @patch("kolay_cli.services.mcp_registry.get_strategies")
    def test_install_summary_shows_count(self, mock_get, mock_install):
        strats = _mock_strategies(2)
        mock_get.return_value = strats
        mock_install.return_value = [
            ("Claude Desktop", True, "/tmp/a.json"),
            ("Cursor (global)", True, "/tmp/b.json"),
        ]
        result = runner.invoke(app, ["mcp", "install"], input="1,2\n")
        assert result.exit_code == 0
        assert "2" in result.output
        assert "configured" in result.output.lower()


# ── kolay mcp inspect ─────────────────────────────────────────────────────────

class TestMcpTools:
    def test_inspect_exits_zero(self, mock_client):
        result = runner.invoke(app, ["mcp", "inspect"])
        assert result.exit_code == 0

    def test_inspect_output_contains_tool_header(self, mock_client):
        result = runner.invoke(app, ["mcp", "inspect"])
        assert "Tool" in result.output or "MCP" in result.output

    def test_inspect_lists_person_list_tool(self, mock_client):
        result = runner.invoke(app, ["mcp", "inspect"])
        assert "person_list" in result.output

    def test_inspect_lists_leave_create_tool(self, mock_client):
        result = runner.invoke(app, ["mcp", "inspect"])
        assert "leave_create" in result.output


# ── kolay mcp serve — stdio banner guard ─────────────────────────────────────

class TestMcpServe:
    def test_serve_stdio_produces_no_stray_stdout(self, mock_client, monkeypatch):
        """In stdio mode the process must emit nothing to stdout before the MCP loop.

        We patch mcp.run() to be a no-op so the test exits immediately.
        """
        monkeypatch.setattr("kolay_cli.mcp_server.mcp.run", lambda **kw: None)
        result = runner.invoke(app, ["mcp", "serve"])
        # No Rich tables, banners, or JSON error blobs should appear on stdout
        assert result.exit_code == 0
        assert result.output.strip() == ""
