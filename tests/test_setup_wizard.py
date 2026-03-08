"""Tests for setup_wizard.py — standalone MCP setup wizard."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure project root is importable
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
_src_dir = _project_root / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))


class TestResolveCommand:
    """Test command resolution for frozen vs. source mode."""

    def test_source_mode_uses_python_m(self):
        from setup_wizard import _resolve_command
        # Ensure sys.frozen is not set (normal source mode)
        with patch.object(sys, "frozen", False, create=True):
            cmd, args = _resolve_command()
            assert cmd == sys.executable
            assert args == ["-m", "kolay_cli.mcp_server"]

    def test_frozen_mode_uses_executable(self):
        from setup_wizard import _resolve_command
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "executable", "/usr/local/bin/kolay-setup"):
                cmd, args = _resolve_command()
                assert cmd == "/usr/local/bin/kolay-setup"
                assert args == ["mcp", "serve"]


class TestStepDisclaimer:
    """Test the disclaimer acceptance step."""

    def test_accept_yes(self):
        from setup_wizard import step_disclaimer
        with patch("setup_wizard.console") as mock_console:
            mock_console.input.return_value = "y"
            assert step_disclaimer() is True

    def test_accept_empty(self):
        from setup_wizard import step_disclaimer
        with patch("setup_wizard.console") as mock_console:
            mock_console.input.return_value = ""
            assert step_disclaimer() is True

    def test_decline_no(self):
        from setup_wizard import step_disclaimer
        with patch("setup_wizard.console") as mock_console:
            mock_console.input.return_value = "n"
            assert step_disclaimer() is False

    def test_decline_random(self):
        from setup_wizard import step_disclaimer
        with patch("setup_wizard.console") as mock_console:
            mock_console.input.return_value = "maybe"
            assert step_disclaimer() is False


class TestStepToken:
    """Test the token input step."""

    def test_valid_token(self):
        from setup_wizard import step_token
        with patch("setup_wizard.console"):
            with patch("getpass.getpass", return_value="my-secret-token"):
                result = step_token()
                assert result == "my-secret-token"

    def test_empty_token_returns_none(self):
        from setup_wizard import step_token
        with patch("setup_wizard.console"):
            with patch("getpass.getpass", return_value=""):
                result = step_token()
                assert result is None

    def test_whitespace_only_returns_none(self):
        from setup_wizard import step_token
        with patch("setup_wizard.console"):
            with patch("getpass.getpass", return_value="   "):
                result = step_token()
                assert result is None

    def test_keyboard_interrupt_returns_none(self):
        from setup_wizard import step_token
        with patch("setup_wizard.console"):
            with patch("getpass.getpass", side_effect=KeyboardInterrupt):
                result = step_token()
                assert result is None

    def test_eof_returns_none(self):
        from setup_wizard import step_token
        with patch("setup_wizard.console"):
            with patch("getpass.getpass", side_effect=EOFError):
                result = step_token()
                assert result is None

    def test_token_is_stripped(self):
        from setup_wizard import step_token
        with patch("setup_wizard.console"):
            with patch("getpass.getpass", return_value="  my-token  "):
                result = step_token()
                assert result == "my-token"


class TestStepStoreToken:
    """Test the token storage step."""

    def test_keychain_success(self):
        from setup_wizard import step_store_token
        with patch("setup_wizard.console"):
            with patch("setup_wizard.store_token", return_value=True) as mock_store:
                result = step_store_token("test-token")
                assert result is True
                mock_store.assert_called_once_with("test-token")

    def test_keychain_fallback(self):
        from setup_wizard import step_store_token
        with patch("setup_wizard.console"):
            with patch("setup_wizard.store_token", return_value=False):
                result = step_store_token("test-token")
                assert result is False


class TestStepSelectClients:
    """Test the client selection step."""

    def test_select_all(self):
        from setup_wizard import step_select_clients
        from kolay_cli.services.mcp_registry import get_strategies
        with patch("setup_wizard.console") as mock_console:
            mock_console.input.return_value = "a"
            result = step_select_clients()
            strategy_names = [s.name for s in get_strategies()]
            assert result == strategy_names

    def test_select_none(self):
        from setup_wizard import step_select_clients
        with patch("setup_wizard.console") as mock_console:
            mock_console.input.return_value = ""
            result = step_select_clients()
            assert result == []

    def test_select_by_number(self):
        from setup_wizard import step_select_clients
        from kolay_cli.services.mcp_registry import get_strategies
        with patch("setup_wizard.console") as mock_console:
            mock_console.input.return_value = "1"
            result = step_select_clients()
            assert result == [get_strategies()[0].name]

    def test_select_multiple_by_number(self):
        from setup_wizard import step_select_clients
        from kolay_cli.services.mcp_registry import get_strategies
        with patch("setup_wizard.console") as mock_console:
            mock_console.input.return_value = "1,2"
            result = step_select_clients()
            strategies = get_strategies()
            assert result == [strategies[0].name, strategies[1].name]

    def test_out_of_range_skipped(self):
        from setup_wizard import step_select_clients
        with patch("setup_wizard.console") as mock_console:
            mock_console.input.return_value = "999"
            result = step_select_clients()
            assert result == []

    def test_invalid_input_skipped(self):
        from setup_wizard import step_select_clients
        with patch("setup_wizard.console") as mock_console:
            mock_console.input.return_value = "abc"
            result = step_select_clients()
            assert result == []


class TestStepInstall:
    """Test the installation step."""

    def test_no_selection_skips(self):
        from setup_wizard import step_install
        with patch("setup_wizard.console"):
            # Should not raise and not call install_mcp_server
            with patch("setup_wizard.install_mcp_server") as mock:
                step_install([])
                mock.assert_not_called()

    def test_calls_install_with_selected(self):
        from setup_wizard import step_install
        with patch("setup_wizard.console"):
            with patch("setup_wizard.install_mcp_server", return_value=[
                ("Claude Desktop", True, "/path/to/config.json"),
            ]) as mock:
                with patch("setup_wizard._resolve_command", return_value=("/usr/bin/python", ["-m", "kolay_cli.mcp_server"])):
                    step_install(["Claude Desktop"])
                    mock.assert_called_once()


class TestMain:
    """Test the main wizard flow."""

    def test_declined_disclaimer_exits_1(self):
        from setup_wizard import main
        with patch("setup_wizard.step_disclaimer", return_value=False):
            with patch("setup_wizard.console"):
                assert main() == 1

    def test_empty_token_exits_2(self):
        from setup_wizard import main
        with patch("setup_wizard.step_disclaimer", return_value=True):
            with patch("setup_wizard.step_token", return_value=None):
                assert main() == 2

    def test_full_flow_exits_0(self):
        from setup_wizard import main
        with patch("setup_wizard.step_disclaimer", return_value=True):
            with patch("setup_wizard.step_token", return_value="token"):
                with patch("setup_wizard.step_store_token", return_value=True):
                    with patch("setup_wizard.step_select_clients", return_value=[]):
                        with patch("setup_wizard.step_install"):
                            with patch("setup_wizard.console"):
                                assert main() == 0


class TestTilde:
    """Test the path display helper."""

    def test_replaces_home(self):
        from setup_wizard import _tilde
        home = str(Path.home())
        assert _tilde(f"{home}/foo/bar") == "~/foo/bar"

    def test_no_home_prefix_unchanged(self):
        from setup_wizard import _tilde
        assert _tilde("/usr/bin/foo") == "/usr/bin/foo"
