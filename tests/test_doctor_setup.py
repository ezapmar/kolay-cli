"""
Tests for ``kolay doctor`` and ``kolay setup`` commands, plus version consistency.
"""
import sys
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from kolay_cli.cli import app

runner = CliRunner()


# ── kolay doctor ──────────────────────────────────────────────────────────────

class TestDoctor:
    """Tests for the ``kolay doctor`` health-check command."""

    @patch("kolay_cli.commands.doctor.shutil")
    @patch("kolay_cli.security.resolve_token", return_value="fake-token")
    @patch("kolay_cli.security.get_keyring_token", return_value="fake-token")
    @patch("kolay_cli.security.validate_token")
    @patch("kolay_cli.commands.doctor.CONFIG_FILE_YAML")
    def test_doctor_all_pass(self, mock_yaml, mock_validate, mock_keyring, mock_resolve, mock_shutil, mock_client):
        """All checks pass output contains 'All clear'."""
        mock_shutil.which.return_value = "/usr/local/bin/kolay"
        mock_yaml.exists.return_value = True
        mock_yaml.__str__ = lambda _: "/fake/config.yaml"

        from kolay_cli.security import TokenStatus
        mock_validate.return_value = TokenStatus(True)

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "All clear" in result.output

    @patch("kolay_cli.commands.doctor.shutil")
    @patch("kolay_cli.security.resolve_token", return_value=None)
    @patch("kolay_cli.commands.doctor.CONFIG_FILE_JSON")
    @patch("kolay_cli.commands.doctor.CONFIG_FILE_YAML")
    def test_doctor_no_token(self, mock_yaml, mock_json, mock_resolve, mock_shutil):
        """No token configured output shows fail marker for token."""
        mock_shutil.which.return_value = "/usr/local/bin/kolay"
        mock_yaml.exists.return_value = False
        mock_json.exists.return_value = False

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "No API token" in result.output

    @patch("kolay_cli.commands.doctor.shutil")
    @patch("kolay_cli.security.resolve_token", return_value=None)
    @patch("kolay_cli.commands.doctor.CONFIG_FILE_JSON")
    @patch("kolay_cli.commands.doctor.CONFIG_FILE_YAML")
    def test_doctor_not_on_path(self, mock_yaml, mock_json, mock_resolve, mock_shutil):
        """Binary not on PATH output shows fail marker."""
        mock_shutil.which.return_value = None
        mock_yaml.exists.return_value = False
        mock_json.exists.return_value = False

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "not" in result.output and "PATH" in result.output


# ── kolay setup ───────────────────────────────────────────────────────────────

class TestSetup:
    """Tests for the ``kolay setup`` wizard."""

    def test_setup_rejects_json_mode(self):
        """Setup wizard should reject --json mode."""
        result = runner.invoke(app, ["--json", "setup"])
        assert result.exit_code == 2

    @patch("kolay_cli.commands.doctor.shutil")
    @patch("kolay_cli.commands.doctor.CONFIG_FILE_YAML")
    @patch("kolay_cli.commands.doctor.CONFIG_FILE_JSON")
    @patch("kolay_cli.commands.setup.get_api_token", return_value="existing-token")
    @patch("kolay_cli.security.resolve_token", return_value="existing-token")
    @patch("kolay_cli.security.get_keyring_token", return_value="existing-token")
    @patch("kolay_cli.security.validate_token")
    def test_setup_skips_auth_when_token_exists(self, mock_validate, mock_keyring, mock_resolve, mock_setup_token, mock_json, mock_yaml, mock_shutil):
        """When a token already exists and user declines reconfigure, auth is skipped."""
        mock_shutil.which.return_value = "/usr/local/bin/kolay"
        mock_yaml.exists.return_value = True
        mock_yaml.__str__ = lambda _: "/fake/config.yaml"
        mock_json.exists.return_value = False

        from kolay_cli.security import TokenStatus
        mock_validate.return_value = TokenStatus(True)

        with patch("kolay_cli.api.client.KolayClient.get") as mock_get:
            mock_get.return_value = {}  # Mock scope check passes
            result = runner.invoke(app, ["setup"], input="n\nn\nn\n")
        
        assert result.exit_code == 0
        assert "already configured" in result.output


# ── version consistency ───────────────────────────────────────────────────────

class TestVersion:
    """Ensure __version__ stays in sync with pyproject.toml."""

    def test_version_matches_pyproject(self):
        """__version__ must match pyproject.toml."""
        from pathlib import Path

        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if not pyproject.exists():
            pytest.skip("pyproject.toml not found")

        if sys.version_info >= (3, 11):
            import tomllib
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            toml_version = data["project"]["version"]
        else:
            # Fallback: simple string parsing
            text = pyproject.read_text()
            for line in text.splitlines():
                if line.strip().startswith("version"):
                    toml_version = line.split("=")[1].strip().strip('"')
                    break
            else:
                pytest.skip("Could not parse version from pyproject.toml")

        from kolay_cli import __version__
        assert __version__ == toml_version, f"__init__.py={__version__} != pyproject.toml={toml_version}"


# ── kolay-mcp TTY guard ──────────────────────────────────────────────────────

class TestMcpEntrypoint:
    """Tests for the kolay-mcp binary UX."""

    def test_mcp_inspect_command(self, mock_client):
        """kolay mcp inspect works and lists registered tools."""
        result = runner.invoke(app, ["mcp", "inspect"])
        assert result.exit_code == 0
        assert "MCP" in result.output or "Tool" in result.output


# ── CLI registration ──────────────────────────────────────────────────────────

class TestCommandRegistration:
    """Verify that new commands show up in help."""

    def test_doctor_in_help(self):
        result = runner.invoke(app, ["--help"])
        assert "doctor" in result.output

    def test_setup_in_help(self):
        result = runner.invoke(app, ["--help"])
        assert "setup" in result.output

    def test_getting_started_panel(self):
        result = runner.invoke(app, ["--help"])
        assert "Getting Started" in result.output
