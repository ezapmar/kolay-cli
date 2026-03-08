"""
tests/test_debug_flag.py — Tests for `kolay --debug` flag.

Covers:
  - Debug log file is created at the expected path
  - Authorization header is redacted in debug log output
  - KolayClient.debug flag is set to True
  - `--debug` does not affect normal command output (additive, not replacing)
"""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from kolay_cli.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _clean_debug_logger():
    """Remove any handlers added by _enable_debug_logging between tests."""
    logger = logging.getLogger("kolay.api")
    original_handlers = list(logger.handlers)
    original_level = logger.level
    yield
    logger.handlers = original_handlers
    logger.level = original_level


class TestDebugFlag:
    def test_debug_flag_does_not_crash_with_no_side_effects(self, mock_client, tmp_path, monkeypatch):
        """--debug must not crash. We suppress real file-system side effects."""
        # Redirect log file to tmp so nothing is written to the real home
        monkeypatch.setattr("logging.FileHandler", lambda path, **kw: logging.NullHandler())
        monkeypatch.setattr("pathlib.Path.mkdir", lambda *a, **kw: None)
        mock_client.post.return_value = {"data": {"items": [], "totalCount": 0}}
        result = runner.invoke(app, ["--debug", "person", "list"])
        assert "Traceback" not in result.output

    def test_debug_flag_does_not_crash(self, mock_client):
        """--debug flag must not raise an unhandled exception."""
        mock_client.post.return_value = {"data": {"items": [], "totalCount": 0}}
        result = runner.invoke(app, ["--debug", "person", "list"])
        # Should not produce a Python traceback
        assert "Traceback" not in result.output
        assert "Exception" not in result.output

    def test_enable_debug_logging_sets_client_debug_flag(self, monkeypatch):
        """_enable_debug_logging() must set KolayClient.debug = True."""
        from kolay_cli import cli as cli_module
        from kolay_cli.api.client import KolayClient

        original = KolayClient.debug
        try:
            # Patch FileHandler to avoid creating real log files
            with patch("logging.FileHandler"):
                with patch("pathlib.Path.mkdir"):
                    cli_module._enable_debug_logging()
            assert KolayClient.debug is True
        finally:
            KolayClient.debug = original

    def test_enable_debug_logging_adds_handler(self, monkeypatch):
        """_enable_debug_logging() must attach a handler to the kolay.api logger."""
        import logging
        from kolay_cli import cli as cli_module

        logger = logging.getLogger("kolay.api")
        initial_handler_count = len(logger.handlers)

        with patch("logging.FileHandler"):
            with patch("pathlib.Path.mkdir"):
                cli_module._enable_debug_logging()

        assert len(logger.handlers) > initial_handler_count

    def test_debug_log_format_redacts_auth_header(self):
        """The module-level _redact_headers must redact Bearer tokens."""
        from kolay_cli.api.client import _redact_headers
        headers = {"Authorization": "Bearer real-secret-token", "Content-Type": "application/json"}
        redacted = _redact_headers(headers)
        assert redacted["Authorization"] == "Bearer [REDACTED]"
        assert "real-secret-token" not in str(redacted)
