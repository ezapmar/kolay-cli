"""
Tests for the security module — keyring storage, JWT validation, require_auth decorator,
token priority chain, migration, and logout.
"""
from __future__ import annotations

import time
import base64
import json
from unittest.mock import MagicMock, patch, call

import pytest
from typer.testing import CliRunner

from kolay_cli.cli import app

runner = CliRunner()


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_jwt(exp_offset: int = 3600, include_exp: bool = True) -> str:
    """Create a minimal JWT with the given exp offset from now."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    payload_data: dict = {}
    if include_exp:
        payload_data["exp"] = int(time.time()) + exp_offset
        payload_data["sub"] = "test-user"
    payload = base64.urlsafe_b64encode(
        json.dumps(payload_data).encode()
    ).rstrip(b"=").decode()
    signature = "fakesignature"
    return f"{header}.{payload}.{signature}"

def _make_expired_jwt() -> str:
    return _make_jwt(exp_offset=-3600)  # 1 hour in the past

def _make_valid_jwt() -> str:
    return _make_jwt(exp_offset=3600)   # 1 hour in the future


# ── Keyring storage ───────────────────────────────────────────────────────────

class TestKeyringSt:
    """Tests for store_token / get_keyring_token / delete_token."""

    @patch("keyring.set_password")
    @patch("keyring.get_password", return_value="my-token")
    def test_store_and_get_round_trip(self, mock_get, mock_set):
        from kolay_cli.security import store_token, get_keyring_token
        result = store_token("my-token")
        assert result is True
        assert get_keyring_token() == "my-token"

    @patch("keyring.delete_password")
    def test_delete_token(self, mock_delete):
        from kolay_cli.security import delete_token
        result = delete_token()
        assert result is True
        mock_delete.assert_called_once()

    @patch("keyring.set_password", side_effect=Exception("no backend"))
    def test_store_falls_back_gracefully(self, mock_set):
        from kolay_cli.security import store_token
        result = store_token("token")
        assert result is False  # keyring unavailable

    @patch("keyring.get_password", return_value=None)
    def test_get_returns_none_when_absent(self, mock_get):
        from kolay_cli.security import get_keyring_token
        assert get_keyring_token() is None


# ── Token resolution priority ─────────────────────────────────────────────────

class TestTokenResolution:
    """Tests for resolve_token() priority chain."""

    def test_env_wins_over_keyring(self, monkeypatch):
        from kolay_cli.security import resolve_token
        monkeypatch.setenv("KOLAY_API_TOKEN", "env-token")
        with patch("kolay_cli.security.get_keyring_token", return_value="keyring-token"):
            assert resolve_token() == "env-token"

    def test_keyring_wins_over_file(self, monkeypatch):
        from kolay_cli.security import resolve_token
        monkeypatch.delenv("KOLAY_API_TOKEN", raising=False)
        with patch("kolay_cli.security.get_keyring_token", return_value="keyring-token"):
            with patch("kolay_cli.security._get_token_from_config_file", return_value="file-token"):
                assert resolve_token() == "keyring-token"

    def test_file_token_as_last_resort(self, monkeypatch):
        from kolay_cli.security import resolve_token
        monkeypatch.delenv("KOLAY_API_TOKEN", raising=False)
        with patch("kolay_cli.security.get_keyring_token", return_value=None):
            with patch("kolay_cli.security._get_token_from_config_file", return_value="file-token"):
                with patch("kolay_cli.security.store_token", return_value=False):
                    result = resolve_token()
                    assert result == "file-token"

    def test_returns_none_when_nothing(self, monkeypatch):
        from kolay_cli.security import resolve_token
        monkeypatch.delenv("KOLAY_API_TOKEN", raising=False)
        with patch("kolay_cli.security.get_keyring_token", return_value=None):
            with patch("kolay_cli.security._get_token_from_config_file", return_value=None):
                assert resolve_token() is None


class TestTokenCache:
    """Tests for in-process caching in resolve_token()."""

    def _reset_cache(self):
        import kolay_cli.security as sec
        sec._token_cache = sec._SENTINEL

    def test_keychain_hit_only_once(self, monkeypatch):
        """After the first resolve, subsequent calls skip the keychain."""
        self._reset_cache()
        monkeypatch.delenv("KOLAY_API_TOKEN", raising=False)

        with patch("kolay_cli.security.get_keyring_token", return_value="cached-token") as mock_kr:
            from kolay_cli.security import resolve_token
            assert resolve_token() == "cached-token"
            assert resolve_token() == "cached-token"
            assert resolve_token() == "cached-token"
            # Keychain should only be called once
            mock_kr.assert_called_once()

    def test_store_token_invalidates_cache(self, monkeypatch):
        """Calling store_token() resets the cache so the new token is returned."""
        self._reset_cache()
        monkeypatch.delenv("KOLAY_API_TOKEN", raising=False)

        with patch("kolay_cli.security.get_keyring_token", side_effect=["old", "new"]):
            with patch("keyring.set_password"):
                with patch("kolay_cli.security._remove_token_from_config_file"):
                    from kolay_cli.security import resolve_token, store_token
                    assert resolve_token() == "old"
                    store_token("new-token")        # invalidates cache
                    assert resolve_token() == "new" # reads keychain again

    def test_delete_token_invalidates_cache(self, monkeypatch):
        """Calling delete_token() resets the cache."""
        self._reset_cache()
        monkeypatch.delenv("KOLAY_API_TOKEN", raising=False)

        with patch("kolay_cli.security.get_keyring_token", side_effect=["token", None]):
            with patch("keyring.delete_password"):
                from kolay_cli.security import resolve_token, delete_token
                assert resolve_token() == "token"
                delete_token()                  # invalidates cache
                assert resolve_token() is None  # no token after logout

    def test_none_not_cached(self, monkeypatch):
        """A None result (no token) is never cached — retries always hit the source."""
        self._reset_cache()
        monkeypatch.delenv("KOLAY_API_TOKEN", raising=False)

        with patch("kolay_cli.security.get_keyring_token", side_effect=[None, "appeared"]):
            from kolay_cli.security import resolve_token
            assert resolve_token() is None      # first call: no token
            assert resolve_token() == "appeared" # token appeared since, should be found



# ── JWT validation ────────────────────────────────────────────────────────────

class TestJWTValidation:
    """Tests for validate_token()."""

    def test_valid_jwt_accepted(self):
        from kolay_cli.security import validate_token
        status = validate_token(_make_valid_jwt())
        assert status.valid is True

    def test_expired_jwt_rejected(self):
        from kolay_cli.security import validate_token
        status = validate_token(_make_expired_jwt())
        assert status.valid is False
        assert "expired" in status.reason.lower()

    def test_opaque_token_accepted(self):
        from kolay_cli.security import validate_token
        # Not a JWT — just a bearer token
        status = validate_token("opaque-bearer-token-abc123")
        assert status.valid is True

    def test_empty_token_rejected(self):
        from kolay_cli.security import validate_token
        status = validate_token("")
        assert status.valid is False

    def test_jwt_without_exp_accepted(self):
        from kolay_cli.security import validate_token
        # JWT with no exp claim — should be accepted (no expiry enforced)
        token = _make_jwt(include_exp=False)
        status = validate_token(token)
        assert status.valid is True

    def test_dotted_opaque_token_treated_as_opaque(self):
        """S1: opaque tokens with two dots must NOT enter the JWT path."""
        from kolay_cli.security import validate_token
        # abc.def.ghi has 3 parts but the header is not valid base64 JSON
        status = validate_token("abc.def.ghi")
        # Must be accepted as opaque (not rejected as a bad JWT)
        assert status.valid is True

    def test_real_jwt_header_still_detected(self):
        """S1: a proper JWT (header starts with {) is still classified as JWT."""
        from kolay_cli.security import _is_jwt
        assert _is_jwt(_make_valid_jwt()) is True

    def test_non_jwt_binary_garbage_not_classified_as_jwt(self):
        """S1: 3-part token where header doesn't decode to JSON is not a JWT."""
        from kolay_cli.security import _is_jwt
        import base64
        # Header encodes to a non-JSON string
        bad_header = base64.urlsafe_b64encode(b"not-json-at-all").decode().rstrip("=")
        assert _is_jwt(f"{bad_header}.payload.sig") is False

    def test_jwt_just_expired_within_skew_accepted(self):
        """S3: token expired 3 seconds ago (within 5-second leeway) is accepted."""
        from kolay_cli.security import validate_token
        # exp = 3 seconds ago — within the 5-second clock-skew leeway
        token = _make_jwt(exp_offset=-3)
        status = validate_token(token)
        assert status.valid is True

    def test_jwt_expired_beyond_skew_rejected(self):
        """S3: token expired 10 seconds ago (beyond leeway) is rejected."""
        from kolay_cli.security import validate_token
        token = _make_jwt(exp_offset=-10)
        status = validate_token(token)
        assert status.valid is False
        assert "expired" in status.reason.lower()

    def test_malformed_jwt_header_treated_as_opaque(self):
        """S1: 3-part string with non-base64 middle treated as opaque (not an error)."""
        from kolay_cli.security import validate_token
        # bad.!!!.sig — header '!!!' is not valid base64, so _is_jwt → False → opaque
        status = validate_token("bad.!!!.sig")
        assert status.valid is True  # opaque passthrough


# ── require_auth decorator ────────────────────────────────────────────────────

class TestRequireAuth:
    """Tests for the require_auth decorator on MCP-style functions."""

    def test_no_token_returns_error_dict(self, monkeypatch):
        from kolay_cli.security import require_auth
        monkeypatch.setenv("KOLAY_API_TOKEN", "")
        monkeypatch.delenv("KOLAY_API_TOKEN", raising=False)

        @require_auth
        def my_tool() -> dict:
            return {"data": "ok"}

        with patch("kolay_cli.security.resolve_token", return_value=None):
            result = my_tool()

        assert result["error"] is True
        assert result["code"] == 401
        assert "token" in result["message"].lower()

    def test_expired_token_returns_error_dict(self):
        from kolay_cli.security import require_auth

        @require_auth
        def my_tool() -> dict:
            return {"data": "ok"}

        with patch("kolay_cli.security.resolve_token", return_value=_make_expired_jwt()):
            result = my_tool()

        assert result["error"] is True
        assert result["code"] == 401

    def test_valid_token_calls_function(self):
        from kolay_cli.security import require_auth

        called = []

        @require_auth
        def my_tool() -> dict:
            called.append(True)
            return {"data": "ok"}

        with patch("kolay_cli.security.resolve_token", return_value="opaque-token"):
            result = my_tool()

        assert result == {"data": "ok"}
        assert called  # function was invoked


# ── Auto-migration ────────────────────────────────────────────────────────────

class TestAutoMigration:
    """Token migration from config file to keychain."""

    def test_file_token_migrates_to_keyring(self, monkeypatch):
        from kolay_cli.security import resolve_token
        monkeypatch.delenv("KOLAY_API_TOKEN", raising=False)

        with patch("kolay_cli.security.get_keyring_token", return_value=None):
            with patch("kolay_cli.security._get_token_from_config_file", return_value="legacy-token"):
                with patch("kolay_cli.security.store_token", return_value=True) as mock_store:
                    result = resolve_token()
                    assert result == "legacy-token"
                    mock_store.assert_called_once_with("legacy-token")


# ── CLI auth commands ─────────────────────────────────────────────────────────

class TestCLIAuthCommands:
    """Integration tests for the CLI auth commands."""

    @patch("kolay_cli.commands.auth.store_token", return_value=True)
    @patch("kolay_cli.commands.auth.KolayClient")
    def test_login_stores_to_keyring(self, mock_client_cls, mock_store):
        mock_client = MagicMock()
        mock_client.get.return_value = {"data": {"firstName": "Test", "lastName": "User"}}
        mock_client_cls.return_value = mock_client

        result = runner.invoke(app, ["auth", "login"], input="my-new-token\n")
        assert result.exit_code == 0
        mock_store.assert_called_once_with("my-new-token")
        assert "Logged In" in result.output or "Authenticated" in result.output

    @patch("kolay_cli.commands.auth.delete_token", return_value=True)
    def test_logout_clears_token(self, mock_delete):
        result = runner.invoke(app, ["auth", "logout"])
        assert result.exit_code == 0
        assert "logged out" in result.output.lower()
        mock_delete.assert_called_once()

    def test_status_no_token(self):
        with patch("kolay_cli.commands.auth.resolve_token_with_source", return_value=(None, "not configured")):
            result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        assert "not logged in" in result.output.lower() or "No API token" in result.output

