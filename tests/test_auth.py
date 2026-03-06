"""Tests for `kolay auth` commands."""
from unittest.mock import patch
from typer.testing import CliRunner
from kolay_cli.cli import app

runner = CliRunner()

ME_RESPONSE = {
    "data": {
        "id": "user1",
        "firstName": "Tunc",
        "lastName": "Aucer",
        "email": "tunc@kolay.com",
        "companyName": "Kolay IK",
    }
}


def test_auth_login_success(mock_client):
    """Login with a token via stdin should save it and confirm."""
    mock_client.get.return_value = ME_RESPONSE
    result = runner.invoke(app, ["auth", "login"], input="my-secret-token\n")
    assert result.exit_code == 0
    # Should confirm login somehow
    assert any(kw in result.output.lower() for kw in ["logged in", "token saved", "authenticated", "welcome", "success", "✔"])


def test_auth_status_logged_in(mock_client):
    """Status command shows profile when token is valid."""
    mock_client.get.return_value = ME_RESPONSE
    result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert any(kw in result.output for kw in ["Tunc", "logged in", "authenticated", "✔"])


def test_auth_status_api_error(mock_client):
    """Status command handles API error gracefully (no traceback)."""
    from kolay_cli.api.errors import APIError
    mock_client.get.side_effect = APIError("Not authorized", status_code=401)
    result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 4  # semantic: auth error
    # Witty or plain error panel rendered — no raw traceback
    assert "Traceback" not in result.output


def test_auth_me(mock_client):
    """Me command renders profile fields."""
    mock_client.get.return_value = ME_RESPONSE
    result = runner.invoke(app, ["auth", "me"])
    assert result.exit_code == 0
    assert "Tunc" in result.output or "tunc@kolay.com" in result.output


def test_auth_bare_shows_hint():
    """Bare `kolay auth` triggers no_command_help, not typer's Missing command."""
    result = runner.invoke(app, ["auth"])
    assert result.exit_code == 0
    assert "Missing command" not in result.output
    assert "sub-command" in result.output
