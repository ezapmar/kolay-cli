from __future__ import annotations

import json
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path


class MCPClientStrategy(ABC):
    """Abstract strategy for injecting an MCP server into a client's configuration."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the client (e.g. 'Claude Desktop')."""
        pass

    @property
    def description(self) -> str:
        """Short description shown in the picker."""
        return ""

    @abstractmethod
    def get_config_path(self) -> Path | None:
        """Return the path to the configuration file, or None if not determinable/supported."""
        pass

    def inject_server(self, server_name: str, command: str, args: list[str]) -> tuple[bool, str]:
        """Inject the MCP server configuration safely. Returns (success, message)."""
        config_path = self.get_config_path()
        if not config_path:
            return False, "Unsupported platform"

        config_data = self._read_config(config_path)
        if isinstance(config_data, tuple):  # (False, error_msg)
            return config_data  # type: ignore[return-value]

        self._set_server(config_data, server_name, command, args)

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(config_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return True, str(config_path)
        except OSError as e:
            return False, f"Failed to write to {config_path}: {e}"

    def _read_config(self, config_path: Path) -> dict | tuple[bool, str]:
        """Read and parse the config file. Returns dict or (False, error)."""
        config_data: dict = {}
        if config_path.exists():
            try:
                content = config_path.read_text(encoding="utf-8").strip()
                if content:
                    config_data = json.loads(content)
            except json.JSONDecodeError:
                return False, f"Invalid JSON in {config_path}. Aborting to prevent data loss."
            except OSError as e:
                return False, f"Could not read {config_path}: {e}"
        return config_data

    def _set_server(self, config_data: dict, server_name: str, command: str, args: list[str]) -> None:
        """Write the server entry into config_data. Override for custom schema."""
        if "mcpServers" not in config_data:
            config_data["mcpServers"] = {}
        elif not isinstance(config_data["mcpServers"], dict):
            config_data["mcpServers"] = {}
        config_data["mcpServers"][server_name] = {
            "command": command,
            "args": args,
        }


# ── Clients ────────────────────────────────────────────────────────────────────


class ClaudeDesktopStrategy(MCPClientStrategy):
    @property
    def name(self) -> str:
        return "Claude Desktop"

    @property
    def description(self) -> str:
        return "Claude desktop app (macOS / Windows)"

    def get_config_path(self) -> Path | None:
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        elif sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "Claude" / "claude_desktop_config.json"
        return Path.home() / ".config" / "claude" / "claude_desktop_config.json"


class CursorProjectStrategy(MCPClientStrategy):
    @property
    def name(self) -> str:
        return "Cursor (project)"

    @property
    def description(self) -> str:
        return "Project-local config (.cursor/mcp.json in cwd)"

    def get_config_path(self) -> Path | None:
        return Path.cwd() / ".cursor" / "mcp.json"


class CursorGlobalStrategy(MCPClientStrategy):
    @property
    def name(self) -> str:
        return "Cursor (global)"

    @property
    def description(self) -> str:
        return "User-global config (~/.cursor/mcp.json)"

    def get_config_path(self) -> Path | None:
        return Path.home() / ".cursor" / "mcp.json"


class WindsurfStrategy(MCPClientStrategy):
    @property
    def name(self) -> str:
        return "Windsurf"

    @property
    def description(self) -> str:
        return "Windsurf IDE (~/.codeium/windsurf/mcp_config.json)"

    def get_config_path(self) -> Path | None:
        return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"


class GeminiCLIStrategy(MCPClientStrategy):
    @property
    def name(self) -> str:
        return "Gemini CLI"

    @property
    def description(self) -> str:
        return "Gemini CLI tool (~/.gemini/settings.json)"

    def get_config_path(self) -> Path | None:
        return Path.home() / ".gemini" / "settings.json"


class VSCodeStrategy(MCPClientStrategy):
    """VS Code with GitHub Copilot (user-level MCP config)."""

    @property
    def name(self) -> str:
        return "VS Code (Copilot)"

    @property
    def description(self) -> str:
        return "VS Code + GitHub Copilot, user-level mcp.json"

    def get_config_path(self) -> Path | None:
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Code" / "User" / "mcp.json"
        elif sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "Code" / "User" / "mcp.json"
        # Linux
        return Path.home() / ".config" / "Code" / "User" / "mcp.json"

    def _set_server(self, config_data: dict, server_name: str, command: str, args: list[str]) -> None:
        # VS Code uses "servers" key (not "mcpServers") with a slightly different schema
        if "servers" not in config_data:
            config_data["servers"] = {}
        elif not isinstance(config_data["servers"], dict):
            config_data["servers"] = {}
        config_data["servers"][server_name] = {
            "command": command,
            "args": args,
        }


class ZedStrategy(MCPClientStrategy):
    """Zed editor — uses context_servers key inside ~/.config/zed/settings.json."""

    @property
    def name(self) -> str:
        return "Zed"

    @property
    def description(self) -> str:
        return "Zed editor (~/.config/zed/settings.json)"

    def get_config_path(self) -> Path | None:
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "Zed" / "settings.json"
        return Path.home() / ".config" / "zed" / "settings.json"

    def _set_server(self, config_data: dict, server_name: str, command: str, args: list[str]) -> None:
        # Zed uses "context_servers" with a {command: {path, args}} structure
        if "context_servers" not in config_data:
            config_data["context_servers"] = {}
        elif not isinstance(config_data["context_servers"], dict):
            config_data["context_servers"] = {}
        config_data["context_servers"][server_name] = {
            "command": {
                "path": command,
                "args": args,
            }
        }


class ChatGPTStrategy(MCPClientStrategy):
    """ChatGPT (OpenAI) -- remote MCP connector via browser UI.

    ChatGPT has no local config file.  The 'install' prints instructions
    and optionally opens the settings page in the default browser.
    """

    @property
    def name(self) -> str:
        return "ChatGPT (OpenAI)"

    @property
    def description(self) -> str:
        return "Remote MCP connector (opens browser instructions)"

    def get_config_path(self) -> Path | None:
        # No local config file -- return a sentinel so inject_server runs.
        return Path.home() / ".chatgpt-mcp-marker"

    def inject_server(self, server_name: str, command: str, args: list[str]) -> tuple[bool, str]:
        """Print connection instructions and offer to open the browser."""
        import webbrowser

        lines = [
            "",
            "  ChatGPT MCP Setup (manual -- no local config file)",
            "",
            "  1. Open chatgpt.com -> profile icon -> Settings",
            "  2. Go to Connectors (under Apps) -> click Add (+)",
            "  3. In the New App dialog, fill in:",
            f"     Name:           {server_name}",
            "     Description:    HR management -- employees, leaves, timelogs, trainings, payroll",
            "     MCP Server URL: https://kolay.up.railway.app/mcp?token=YOUR_KOLAY_API_TOKEN",
            '     Authentication: select "No Auth"',
            '  4. Check "I understand and want to continue"',
            "  5. Click Create",
            "",
        ]

        try:
            from rich.console import Console
            from ..ui.constants import PRIMARY
            c = Console(highlight=False)
            for line in lines:
                c.print(f"[grey85]{line}[/grey85]")
        except Exception:
            for line in lines:
                print(line)

        try:
            webbrowser.open("https://chatgpt.com/settings")
        except Exception:
            pass

        return True, "Instructions printed (browser opened)"


# ── Registry ───────────────────────────────────────────────────────────────────


def get_strategies() -> list[MCPClientStrategy]:
    return [
        ClaudeDesktopStrategy(),
        CursorGlobalStrategy(),
        CursorProjectStrategy(),
        WindsurfStrategy(),
        GeminiCLIStrategy(),
        VSCodeStrategy(),
        ZedStrategy(),
        ChatGPTStrategy(),
    ]


def install_mcp_server(
    server_name: str,
    command: str,
    args: list[str],
    selected: list[str] | None = None,
) -> list[tuple[str, bool, str]]:
    """Install the MCP server into the selected clients.

    Args:
        server_name: Key written into the config (e.g. ``"kolay-ik"``).
        command:     Executable path.
        args:        Argument list.
        selected:    Strategy names to install. ``None`` means all.

    Returns:
        List of ``(client_name, success, path_or_error_msg)``.
    """
    results = []
    strategies = get_strategies()
    for strategy in strategies:
        if selected is not None and strategy.name not in selected:
            continue
        config_path = strategy.get_config_path()
        if not config_path:
            results.append((strategy.name, False, "Unsupported platform"))
            continue

        success, msg = strategy.inject_server(server_name, command, args)
        results.append((strategy.name, success, msg))

    return results
