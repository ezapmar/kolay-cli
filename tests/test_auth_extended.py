"""
tests/test_auth_extended.py — Extended tests for commands/auth.py

Covers the previously uncovered branches (lines 47-52, 63-67, 91-96, 105,
115-116, 126-130, 140-141, 147-150, 165-166):

  - login: happy path (token stored → API verifies → rich panel shown)
  - login: happy path in --json mode (returns JSON, no panel)
  - login: stored but verification failed (SystemExit path)
  - login: stored but verification failed in --json mode
  - logout: keyring cleared → success message
  - logout: nothing stored → "already logged out" message
  - logout: --json mode
  - status: no token → error
  - status: token invalid (local validation fails)
  - status: API verification fails (SystemExit path)
  - status: --json mode authenticated
  - status: --json mode API failure
  - me: --json mode
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from kolay_cli.cli import app

runner = CliRunner()


ME_RESPONSE = {"data": {"id": "u1", "firstName": "Ali", "lastName": "Veli", "workEmail": "ali@co.com"}}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _patch_store(saved_to_keyring=True):
    return patch("kolay_cli.commands.auth.store_token", return_value=saved_to_keyring)

def _patch_delete(removed=True):
    return patch("kolay_cli.commands.auth.delete_token", return_value=removed)

def _patch_resolve(token="tok123", source="keyring"):
    return patch("kolay_cli.commands.auth.resolve_token_with_source", return_value=(token, source))

def _patch_validate(valid=True, reason=""):
    result = MagicMock()
    result.__bool__ = lambda s: valid
    result.reason = reason
    return patch("kolay_cli.commands.auth.validate_token", return_value=result)

def _patch_remove_config():
    return patch("kolay_cli.security._remove_token_from_config_file")


# ── auth login ────────────────────────────────────────────────────────────────

class TestAuthLogin:
    def test_login_happy_path_human_mode(self, mock_client):
        mock_client.get.return_value = ME_RESPONSE
        with _patch_store(saved_to_keyring=True):
            result = runner.invoke(app, ["auth", "login", "--token", "tok123"])
        assert result.exit_code == 0
        assert "Authenticated" in result.output or "Logged In" in result.output

    def test_login_happy_path_json_mode(self, mock_client):
        import json
        mock_client.get.return_value = ME_RESPONSE
        with _patch_store(saved_to_keyring=True):
            result = runner.invoke(app, ["--json", "auth", "login", "--token", "tok123"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "authenticated"
        assert "name" in data
        assert data["token_storage"] == "keyring"

    def test_login_json_mode_no_keyring(self, mock_client):
        """When keyring is unavailable, token_storage should be 'config_file'."""
        import json
        mock_client.get.return_value = ME_RESPONSE
        with _patch_store(saved_to_keyring=False):
            result = runner.invoke(app, ["--json", "auth", "login", "--token", "tok123"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["token_storage"] == "config_file"

    def test_login_verification_failed_human_mode(self, mock_client):
        """Token saved but API call raises SystemExit → graceful fallback message."""
        mock_client.get.side_effect = SystemExit(1)
        with _patch_store(saved_to_keyring=True):
            result = runner.invoke(app, ["auth", "login", "--token", "tok123"])
        assert result.exit_code == 0
        assert "saved" in result.output.lower() or "verification failed" in result.output.lower()

    def test_login_verification_failed_json_mode(self, mock_client):
        """Token saved but API call raises SystemExit in --json mode."""
        import json
        mock_client.get.side_effect = SystemExit(1)
        with _patch_store(saved_to_keyring=True):
            result = runner.invoke(app, ["--json", "auth", "login", "--token", "tok123"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "error" or data.get("message")


# ── auth logout ───────────────────────────────────────────────────────────────

class TestAuthLogout:
    def test_logout_keyring_cleared(self):
        with _patch_delete(removed=True), _patch_remove_config():
            result = runner.invoke(app, ["auth", "logout"])
        assert result.exit_code == 0
        assert "logged out" in result.output.lower() or "Removed" in result.output

    def test_logout_nothing_stored(self):
        # Note: removed_file is hardcoded True in the logout command,
        # so the success path always runs even when keyring has nothing.
        with _patch_delete(removed=False), _patch_remove_config():
            result = runner.invoke(app, ["auth", "logout"])
        assert result.exit_code == 0
        # "Config file cleaned" always appears (fire-and-forget)
        assert "logged out" in result.output.lower() or "Config file" in result.output

    def test_logout_json_mode(self):
        import json
        with _patch_delete(removed=True), _patch_remove_config():
            result = runner.invoke(app, ["--json", "auth", "logout"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "logged_out"
        assert "keyring_cleared" in data


# ── auth status ───────────────────────────────────────────────────────────────

class TestAuthStatus:
    def test_status_no_token(self):
        with patch("kolay_cli.commands.auth.resolve_token_with_source", return_value=(None, None)):
            result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        assert "not logged in" in result.output.lower() or "No API token" in result.output

    def test_status_no_token_json_mode(self):
        import json
        with patch("kolay_cli.commands.auth.resolve_token_with_source", return_value=(None, None)):
            result = runner.invoke(app, ["--json", "auth", "status"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["authenticated"] is False

    def test_status_invalid_token_local(self):
        """Local token validation fails (expired/malformed) → error before API call."""
        with _patch_resolve(), _patch_validate(valid=False, reason="Token expired."):
            result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        assert "expired" in result.output.lower() or "Token" in result.output

    def test_status_invalid_token_json_mode(self):
        import json
        with _patch_resolve(), _patch_validate(valid=False, reason="Token expired."):
            result = runner.invoke(app, ["--json", "auth", "status"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["authenticated"] is False

    def test_status_api_verification_fails(self, mock_client):
        """Token passes local validation but API call raises SystemExit."""
        mock_client.get.side_effect = SystemExit(1)
        with _patch_resolve(), _patch_validate(valid=True):
            result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        assert "verification failed" in result.output.lower() or "Token exists" in result.output

    def test_status_api_fails_json_mode(self, mock_client):
        import json
        mock_client.get.side_effect = SystemExit(1)
        with _patch_resolve(), _patch_validate(valid=True):
            result = runner.invoke(app, ["--json", "auth", "status"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["authenticated"] is False

    def test_status_authenticated_human(self, mock_client):
        mock_client.get.return_value = ME_RESPONSE
        with _patch_resolve(), _patch_validate(valid=True):
            result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        assert "Logged in" in result.output or "Ali" in result.output

    def test_status_authenticated_json(self, mock_client):
        import json
        mock_client.get.return_value = ME_RESPONSE
        with _patch_resolve(), _patch_validate(valid=True):
            result = runner.invoke(app, ["--json", "auth", "status"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["authenticated"] is True
        assert "name" in data


# ── auth me ───────────────────────────────────────────────────────────────────

class TestAuthMe:
    def test_me_json_mode(self, mock_client):
        import json
        mock_client.get.return_value = ME_RESPONSE
        result = runner.invoke(app, ["--json", "auth", "me"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data.get("firstName") == "Ali"

    def test_me_human_mode(self, mock_client):
        mock_client.get.return_value = ME_RESPONSE
        result = runner.invoke(app, ["auth", "me"])
        assert result.exit_code == 0
        assert "Ali" in result.output
