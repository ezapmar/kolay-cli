"""
Tests for ui/formatters.py and ui/messages.py helpers.

Covers:
  - short_id, display_status, fmt_val, fmt_num, label
  - print_error, print_success, print_empty renders (via console capture)
  - print_api_error: witty panel for 401/403/429/500, plain fallback for 404
  - get_scenario: all mapped codes return a 3-tuple; unknown code returns None
  - no_command_help: hint + Usage appear in output, exits 0
  - APIError: message, status_code, hint auto-populated
"""
import pytest
from io import StringIO
from rich.console import Console

from kolay_cli.ui.formatters import (
    short_id, display_status, fmt_val, fmt_num, label,
    print_error, print_success, print_empty, no_command_help,
)
from kolay_cli.ui.messages import get_scenario
from kolay_cli.api.errors import APIError, HTTP_ERRORS


# ── Helpers to capture rich output ───────────────────────────────────────────

def _capture(fn, *args, **kwargs) -> str:
    """Run fn and return the plain-text output it prints to the console."""
    buf = StringIO()
    c = Console(file=buf, highlight=False, no_color=True)
    import kolay_cli.ui.formatters as mod
    orig = mod.console
    mod.console = c
    try:
        fn(*args, **kwargs)
    finally:
        mod.console = orig
    return buf.getvalue()


# ── short_id ─────────────────────────────────────────────────────────────────

class TestShortId:
    def test_long_id_truncated(self):
        result = short_id("abc123def456abc123de")
        assert "abc123de" in result          # last 8 chars present
        assert "…" in result

    def test_short_id_no_ellipsis(self):
        result = short_id("abc123")
        assert "…" not in result
        assert "abc123" in result

    def test_empty_returns_dash(self):
        assert "—" in short_id("")

    def test_na_returns_dash(self):
        assert "—" in short_id("N/A")

    def test_dash_returns_dash(self):
        assert "—" in short_id("—")


# ── display_status ────────────────────────────────────────────────────────────

class TestDisplayStatus:
    def test_approved_styled(self):
        out = display_status("approved")
        assert "approved" in out.lower()

    def test_waiting_styled(self):
        out = display_status("waiting")
        assert "waiting" in out.lower()

    def test_unknown_falls_back(self):
        out = display_status("custom_status")
        assert "custom_status" in out

    def test_empty_returns_dash(self):
        assert "—" in display_status("")


# ── fmt_val ───────────────────────────────────────────────────────────────────

class TestFmtVal:
    def test_none_returns_dash(self):
        assert "—" in fmt_val(None)

    def test_empty_str_returns_dash(self):
        assert "—" in fmt_val("")

    def test_true_shows_yes(self):
        assert "Yes" in fmt_val(True)

    def test_false_shows_no(self):
        assert "No" in fmt_val(False)

    def test_string_passthrough(self):
        assert fmt_val("hello") == "hello"

    def test_integer_passthrough(self):
        assert "42" in fmt_val(42)


# ── fmt_num ───────────────────────────────────────────────────────────────────

class TestFmtNum:
    def test_integer_float_strips_dot(self):
        assert fmt_num(3.0) == "3"

    def test_real_float_keeps_decimal(self):
        assert fmt_num(3.5) == "3.5"

    def test_none_returns_dash(self):
        assert "—" in fmt_num(None)

    def test_invalid_returns_str(self):
        assert fmt_num("abc") == "abc"


# ── label ──────────────────────────────────────────────────────────────────────

class TestLabel:
    def test_known_key_returns_label(self):
        # "firstName" should map to something human-readable
        result = label("firstName")
        assert result  # non-empty

    def test_unknown_key_titlecased(self):
        result = label("someRandomKey")
        # Falls back to title-casing
        assert result[0].isupper()


# ── print_error ───────────────────────────────────────────────────────────────

class TestPrintError:
    def test_message_appears(self):
        out = _capture(print_error, "Something broke badly")
        assert "Something broke badly" in out

    def test_hint_appears(self):
        out = _capture(print_error, "Broken", hint="Try rebooting")
        assert "Try rebooting" in out

    def test_strips_api_error_prefix(self):
        out = _capture(print_error, "API Error: Too bad")
        assert "API Error:" not in out
        assert "Too bad" in out


# ── print_success / print_empty ───────────────────────────────────────────────

class TestPrintHelpers:
    def test_success_contains_checkmark(self):
        out = _capture(print_success, "All done!")
        assert "" in out
        assert "All done!" in out

    def test_empty_shows_entity(self):
        out = _capture(print_empty, "spacecrafts")
        assert "spacecrafts" in out

    def test_empty_shows_hint(self):
        out = _capture(print_empty, "spacecrafts", hint="Try NASA.")
        assert "Try NASA." in out


# ── APIError ──────────────────────────────────────────────────────────────────

class TestAPIError:
    def test_message_stored(self):
        err = APIError("Something bad")
        assert err.message == "Something bad"
        assert str(err) == "Something bad"

    def test_hint_auto_populated_for_known_status(self):
        err = APIError("Unauthorized", status_code=401)
        assert err.hint is not None
        assert len(err.hint) > 0

    def test_hint_none_for_unknown_status(self):
        err = APIError("Unknown", status_code=418)
        assert err.hint is None

    def test_explicit_hint_overrides(self):
        err = APIError("Oops", status_code=401, hint="Custom hint")
        assert err.hint == "Custom hint"

    def test_status_code_stored(self):
        err = APIError("Gone", status_code=410)
        assert err.status_code == 410

    @pytest.mark.parametrize("code", [400, 401, 403, 404, 422, 429, 500, 502, 503, 504])
    def test_all_http_errors_have_message_and_hint(self, code):
        msg, hint = HTTP_ERRORS[code]
        assert msg
        assert hint


# ── get_scenario (ui/messages.py) ─────────────────────────────────────────────

class TestGetScenario:
    @pytest.mark.parametrize("code", [401, 403, 429, 500, 502, 503])
    def test_witty_codes_return_tuple(self, code):
        result = get_scenario(code)
        assert result is not None
        headline, body, hint = result
        assert headline
        assert body
        assert hint

    def test_unmapped_code_returns_none(self):
        assert get_scenario(404) is None
        assert get_scenario(418) is None

    def test_401_has_login_hint(self):
        headline, body, hint = get_scenario(401)
        assert "login" in hint.lower() or "token" in hint.lower()

    def test_403_has_admin_hint(self):
        headline, body, hint = get_scenario(403)
        assert "admin" in hint.lower() or "scope" in hint.lower()


# ── print_api_error ────────────────────────────────────────────────────────────

class TestPrintApiError:
    def _run(self, status_code: int, message: str = "Error") -> str:
        from kolay_cli.ui.formatters import print_api_error
        err = APIError(message, status_code=status_code)
        return _capture(print_api_error, err)

    def test_401_shows_witty_panel(self):
        out = self._run(401)
        # Witty headline (one of the 401 scenarios) should contain an emoji hint
        assert any(kw in out for kw in ["library card", "expired", "key", "Post-it", "door"])

    def test_403_shows_witty_panel(self):
        out = self._run(403)
        assert any(kw in out for kw in ["shred", "VIP", "floor", "Management"])

    def test_429_shows_witty_panel(self):
        out = self._run(429)
        assert any(kw in out for kw in ["slow", "hammering", "breathe"])

    def test_500_shows_witty_panel(self):
        out = self._run(500)
        assert any(kw in out for kw in ["sneezed", "hamsters"])

    def test_404_falls_back_to_plain_panel(self):
        err = APIError("Resource not found", status_code=404, hint="Check the ID")
        from kolay_cli.ui.formatters import print_api_error
        out = _capture(print_api_error, err)
        assert "Resource not found" in out

    def test_no_status_uses_plain_panel(self):
        err = APIError("Generic failure")
        from kolay_cli.ui.formatters import print_api_error
        out = _capture(print_api_error, err)
        assert "Generic failure" in out


# ── no_command_help ───────────────────────────────────────────────────────────

class TestNoCommandHelp:
    def test_shows_hint_and_help(self):
        """Invoke auth with no subcommand — should get hint + usage."""
        from typer.testing import CliRunner
        from kolay_cli.cli import app
        r = CliRunner()
        result = r.invoke(app, ["auth"])
        assert result.exit_code == 0
        assert "sub-command" in result.output
        assert "kolay auth" in result.output
        assert "Usage:" in result.output

    def test_subcommand_skips_hint(self):
        """Invoking a real subcommand must NOT trigger the no_command_help hint."""
        from typer.testing import CliRunner
        from kolay_cli.cli import app
        r = CliRunner()
        result = r.invoke(app, ["auth", "--help"])
        assert result.exit_code == 0
        assert "sub-command" not in result.output
