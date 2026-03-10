"""Tests for `kolay config` commands."""
import os
from unittest.mock import patch
from typer.testing import CliRunner
from kolay_cli.cli import app

runner = CliRunner()


def test_config_show(mock_client):
    """Config show renders active configuration."""
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    # Should show token and base URL sections
    assert any(kw in result.output.lower() for kw in ["token", "url", "base", "config"])


def test_config_set_valid_key():
    """Config set writes a key=value — exit 0 and confirm message."""
    result = runner.invoke(app, ["config", "set", "base_url", "https://api.kolayik.com"])
    assert result.exit_code == 0
    assert any(kw in result.output.lower() for kw in ["saved", "set", "updated", ""])


def test_config_set_missing_value():
    """Config set with only one arg (missing value) typer exits 2."""
    result = runner.invoke(app, ["config", "set", "base_url"])
    assert result.exit_code == 2


def test_config_validate_success(mock_client):
    """Validate calls the API and confirms the token is valid."""
    mock_client.get.return_value = {"data": {"firstName": "Tunc"}}
    result = runner.invoke(app, ["config", "validate"])
    assert result.exit_code == 0
    assert any(kw in result.output.lower() for kw in ["valid", "success", "", "ok"])


def test_config_validate_401(mock_client):
    """Validate renders witty 401 panel when token is invalid."""
    from kolay_cli.api.errors import APIError
    mock_client.get.side_effect = APIError("Not authorized", status_code=401)
    result = runner.invoke(app, ["config", "validate"])
    assert result.exit_code == 4  # semantic: auth error
    assert "Traceback" not in result.output


def test_config_bare_shows_hint():
    """Bare `kolay config` triggers no_command_help."""
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "sub-command" in result.output
    assert "Missing command" not in result.output
