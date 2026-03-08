"""
CLI integration tests — the root `kolay` app entrypoint.

Covers:
  - --version flag
  - Bare invocation (logo + help)
  - Bare command-group invocation → no_command_help countdown
  - Unknown command → typer error (exit 2)
"""
import pytest
from typer.testing import CliRunner
from kolay_cli.cli import app

runner = CliRunner()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Kolay CLI" in result.output


def test_bare_invocation_shows_help():
    """Running `kolay` with no args must print the logo area + command list."""
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    # Logo characters appear somewhere
    assert "+" in result.output or "%" in result.output
    # Help panel appears
    assert "person" in result.output
    assert "leave" in result.output


def test_help_flag():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Authentication" in result.output
    assert "People" in result.output
    assert "Finance" in result.output


# ── no_command_help: bare command-group invocations ──────────────────────────

@pytest.mark.parametrize("group", [
    "auth", "person", "leave", "timelog", "training",
    "transaction", "expense", "approval", "calendar", "unit", "config",
])
def test_bare_command_group_shows_hint_then_help(group, mock_client):
    """Any bare `kolay <group>` must show the hint and then the help text."""
    result = runner.invoke(app, [group])
    assert result.exit_code == 0, f"{group!r} exited {result.exit_code}: {result.output}"
    # Hint line
    assert f"kolay {group}" in result.output
    assert "sub-command" in result.output
    # Help follows
    assert "Usage:" in result.output


def test_unknown_command_exits_nonzero():
    result = runner.invoke(app, ["doesnotexist"])
    assert result.exit_code != 0


# ── Alpha release warnings ────────────────────────────────────────────────────

def test_help_shows_alpha_release_label():
    """Root --help must show the ALPHA RELEASE label."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ALPHA" in result.output


def test_help_shows_unofficial_disclaimer():
    """Root --help must warn the user this is unofficial / experimental."""
    result = runner.invoke(app, ["--help"])
    assert "unofficial" in result.output.lower() or "experimental" in result.output.lower()


def test_version_flag_shows_alpha_tag():
    """--version must include the 'alpha' string so users know the maturity level."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "alpha" in result.output.lower()
