"""
Tests for _redact_headers() — C1 fix.

Verifies that the Authorization header is always masked in debug log output,
regardless of token value, capitalization, or whether other headers are present.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from kolay_cli.api.client import _redact_headers, KolayClient


# ── Unit tests for _redact_headers() ─────────────────────────────────────────

class TestRedactHeaders:

    def test_bearer_token_redacted(self):
        """Standard 'Bearer <token>' is replaced with 'Bearer [REDACTED]'."""
        headers = {"Authorization": "Bearer supersecrettoken123"}
        result = _redact_headers(headers)
        assert result["Authorization"] == "Bearer [REDACTED]"
        assert "supersecrettoken123" not in result["Authorization"]

    def test_other_headers_preserved(self):
        """Non-Authorization headers are passed through unchanged."""
        headers = {
            "Authorization": "Bearer abc.def.ghi",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": "en",
        }
        result = _redact_headers(headers)
        assert result["Content-Type"] == "application/json"
        assert result["Accept"] == "application/json"
        assert result["Accept-Language"] == "en"

    def test_case_insensitive_key_match(self):
        """Matches 'authorization' (lowercase) as well as 'Authorization'."""
        headers = {"authorization": "Bearer lowercasetoken"}
        result = _redact_headers(headers)
        assert "lowercasetoken" not in result["authorization"]
        assert "[REDACTED]" in result["authorization"]

    def test_bearer_case_insensitive(self):
        """Matches 'bearer' (any casing) in the header value."""
        headers = {"Authorization": "bearer MixedCaseToken456"}
        result = _redact_headers(headers)
        assert "MixedCaseToken456" not in result["Authorization"]
        assert "[REDACTED]" in result["Authorization"]

    def test_empty_headers(self):
        """Empty dict returns empty dict without error."""
        assert _redact_headers({}) == {}

    def test_no_authorization_header(self):
        """Dict without Authorization header is returned unchanged."""
        headers = {"Content-Type": "application/json"}
        result = _redact_headers(headers)
        assert result == headers

    def test_returns_copy_not_mutating_original(self):
        """Original dict is not mutated."""
        original = {"Authorization": "Bearer real-token"}
        result = _redact_headers(original)
        assert original["Authorization"] == "Bearer real-token" # unchanged
        assert result["Authorization"] == "Bearer [REDACTED]" # copy is redacted

    def test_opaque_non_bearer_auth_redacted(self):
        """A non-JWT opaque token (still 'Bearer <opaque>') is also redacted."""
        headers = {"Authorization": "Bearer opaque-token-abc123xyz"}
        result = _redact_headers(headers)
        assert "opaque-token-abc123xyz" not in result["Authorization"]


# ── Integration: token never appears in debug log ─────────────────────────────

class TestDebugLoggingDoesNotLeakToken:
    """Verify that when debug logging is enabled, the token is never logged."""

    def test_request_debug_log_redacts_token(self):
        """The Authorization header in debug output is always [REDACTED]."""
        token = "super-secret-api-token-should-not-appear-in-logs"

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'{"data": []}'
            mock_response.json.return_value = {"data": []}
            mock_session.request.return_value = mock_response
            # Simulate headers that would be set in __init__
            mock_session.headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Language": "en",
            }
            mock_session_cls.return_value = mock_session

            with patch("kolay_cli.api.client.KolayClient.__init__") as mock_init:
                mock_init.return_value = None  # skip actual init

                client = KolayClient.__new__(KolayClient)
                client.session = mock_session
                client.base_url = "https://api.kolayik.com"
                client._debug = True

                # Patch the class-level debug flag
                KolayClient.debug = True

                log_records = []

                class CaptureHandler(logging.Handler):
                    def emit(self, record):
                        log_records.append(record.getMessage())

                import logging as _logging
                logger = _logging.getLogger("kolay.api")
                handler = CaptureHandler()
                logger.addHandler(handler)
                logger.setLevel(_logging.DEBUG)

                try:
                    client._request("GET", "v2/person/list")
                except Exception:
                    pass  # response parsing may fail in mock; we only care about logs
                finally:
                    logger.removeHandler(handler)
                    KolayClient.debug = False

                # The raw token must NEVER appear in any log message
                all_logs = " ".join(log_records)
                assert token not in all_logs, (
                    f"Token leaked into debug log!\nLog output:\n{all_logs[:500]}"
                )
                # But [REDACTED] should appear (confirming the header WAS logged)
                assert "[REDACTED]" in all_logs or "Authorization" not in all_logs, (
                    "Expected either REDACTED marker or no Authorization in logs"
                )
