"""
Tests for C2 fix — KolayClient token not exposed via repr/str/tracebacks.

Verifies that:
- __repr__ and __str__ never contain the raw token
- The attribute is private (_token), not public (token)
- Exception tracebacks that include the client object don't leak the token
"""
from __future__ import annotations

import traceback
from unittest.mock import MagicMock, patch

import pytest


def _make_client(token: str = "secret-bearer-token") -> "KolayClient":
    """Create a KolayClient with a mocked session (no network)."""
    from kolay_cli.api.client import KolayClient
    with patch("requests.Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session.headers = {}
        mock_session_cls.return_value = mock_session
        with patch("kolay_cli.api.client.config") as mock_config:
            mock_config.get_api_token.return_value = token
            mock_config.get_base_url.return_value = "https://api.kolayik.com"
            return KolayClient(token=token)


class TestKolayClientSafeRepr:

    def test_repr_does_not_contain_token(self):
        """repr(client) must never include the raw bearer token."""
        token = "super-secret-repr-token"
        client = _make_client(token)
        r = repr(client)
        assert token not in r
        assert "[REDACTED]" not in r  # also not "redacted" — just omitted
        assert "KolayClient" in r

    def test_str_does_not_contain_token(self):
        """str(client) must never include the raw bearer token."""
        token = "super-secret-str-token"
        client = _make_client(token)
        assert token not in str(client)

    def test_repr_contains_base_url(self):
        """repr should still be useful — contain the base URL."""
        client = _make_client()
        assert "api.kolayik.com" in repr(client)

    def test_token_attribute_is_private(self):
        """Public `.token` attribute must not exist; `._token` is private."""
        client = _make_client("my-token")
        assert not hasattr(client, "token"), (
            "KolayClient.token (public) exposes the bearer token — use ._token instead"
        )
        assert hasattr(client, "_token")

    def test_token_not_in_exception_traceback(self):
        """If KolayClient appears in a traceback, the token must not be visible."""
        token = "traceback-leak-test-token"
        client = _make_client(token)

        tb_text = ""
        try:
            raise ValueError(f"Something broke: {client!r}")
        except ValueError:
            tb_text = traceback.format_exc()

        assert token not in tb_text, (
            f"Token leaked into traceback!\nTraceback:\n{tb_text}"
        )

    def test_f_string_interpolation_does_not_leak_token(self):
        """f'...{client}...' must not expose the token."""
        token = "fstring-leak-test-token"
        client = _make_client(token)
        rendered = f"Debug: client={client}"
        assert token not in rendered

    def test_format_does_not_leak_token(self):
        """'{}'.format(client) must not expose the token."""
        token = "format-leak-test-token"
        client = _make_client(token)
        rendered = "Client: {}".format(client)
        assert token not in rendered
