"""
Shared pytest fixtures and helpers for kolay-cli tests.
"""
import os
import pytest
from unittest.mock import MagicMock
from typer.testing import CliRunner

# ── Environment setup — must happen before any app import ─────────────────────
os.environ.setdefault("KOLAY_API_TOKEN", "test-token-fixture")
os.environ.setdefault("KOLAY_BASE_URL", "https://api.kolayik.com")

from kolay_cli.cli import app
from kolay_cli.api import KolayClient





@pytest.fixture(autouse=True)
def reset_output_modes():
    """Reset json_mode and yes_mode between tests to prevent leaking."""
    from kolay_cli.ui.output import set_json_mode, set_yes_mode
    set_json_mode(False)
    set_yes_mode(False)
    yield
    set_json_mode(False)
    set_yes_mode(False)


@pytest.fixture(autouse=True)
def reset_token_cache():
    """Reset the in-process token cache between tests to prevent state leaking."""
    import kolay_cli.security as sec
    sec._token_cache = sec._SENTINEL
    yield
    sec._token_cache = sec._SENTINEL



@pytest.fixture
def runner():
    """Typer CLI test runner (no colour simple string assertions)."""
    return CliRunner()


@pytest.fixture
def mock_client(monkeypatch):
    """
    Replace KolayClient in every command AND service module with a MagicMock.

    Usage::

        def test_something(mock_client):
            mock_client.get.return_value = {"data": [...]}
            result = runner.invoke(app, ["person", "list"])
    """
    client_mock = MagicMock(spec=KolayClient)
    client_mock.base_url = "https://api.kolayik.com"

    def _patch(*_args, **_kwargs):
        return client_mock

    # Patch KolayClient in command modules (some still import it directly)
    cmd_modules = [
        "person", "leave", "transaction", "calendar",
        "timelog", "training", "unit", "expense",
        "approval", "auth", "nudge", "payroll",
    ]
    for mod in cmd_modules:
        try:
            monkeypatch.setattr(f"kolay_cli.commands.{mod}.KolayClient", _patch)
        except AttributeError:
            pass  # module no longer imports KolayClient directly

    # Patch KolayClient in service modules (the new single source of truth)
    svc_modules = [
        "person", "leave", "timelog", "training", "transaction",
        "calendar", "unit", "approval", "expense", "nudge", "payroll",
    ]
    for mod in svc_modules:
        try:
            monkeypatch.setattr(f"kolay_cli.services.{mod}.KolayClient", _patch)
        except AttributeError:
            pass

    # Also patch at the API-client level so config validate() gets the mock too
    monkeypatch.setattr("kolay_cli.api.client.KolayClient.__init__",
                        lambda self, *a, **kw: None)
    monkeypatch.setattr("kolay_cli.api.KolayClient", _patch)

    return client_mock

