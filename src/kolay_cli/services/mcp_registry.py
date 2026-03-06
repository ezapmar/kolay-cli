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

    @abstractmethod
    def get_config_path(self) -> Path | None:
        """Return the path to the configuration file, or None if not determinable/supported."""
        pass

    def inject_server(self, server_name: str, command: str, args: list[str]) -> tuple[bool, str]:
        """Inject the MCP server configuration safely. Returns (success, message)."""
        config_path = self.get_config_path()
        if not config_path:
            return False, "Unsupported platform"

        config_data = {}
        if config_path.exists():
            try:
                content = config_path.read_text(encoding="utf-8").strip()
                if content:
                    config_data = json.loads(content)
            except json.JSONDecodeError:
                return False, f"Invalid JSON in {config_path}. Aborting to prevent data loss."
            except OSError as e:
                return False, f"Could not read {config_path}: {e}"

        # Most systems (Claude, Cursor, Windsurf) use the "mcpServers" key structure.
        if "mcpServers" not in config_data:
            config_data["mcpServers"] = {}
        elif not isinstance(config_data["mcpServers"], dict):
            return False, f"'mcpServers' is not a dictionary in {config_path}."

        config_data["mcpServers"][server_name] = {
            "command": command,
            "args": args,
        }

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(config_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return True, str(config_path)
        except OSError as e:
            return False, f"Failed to write to {config_path}: {e}"


class ClaudeDesktopStrategy(MCPClientStrategy):
    @property
    def name(self) -> str:
        return "Claude Desktop"

    def get_config_path(self) -> Path | None:
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        elif sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "Claude" / "claude_desktop_config.json"
        # Linux doesn't have an official Claude Desktop app yet, but sometimes unofficial ports use ~/.config
        return Path.home() / ".config" / "claude" / "claude_desktop_config.json"


class CursorProjectStrategy(MCPClientStrategy):
    @property
    def name(self) -> str:
        return "Cursor IDE (Project)"

    def get_config_path(self) -> Path | None:
        # Project-specific Cursor MCP
        return Path.cwd() / ".cursor" / "mcp.json"


class WindsurfStrategy(MCPClientStrategy):
    @property
    def name(self) -> str:
        return "Windsurf"

    def get_config_path(self) -> Path | None:
        # Windsurf generally uses standard Codeium paths for MCP
        return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"


def get_strategies() -> list[MCPClientStrategy]:
    return [
        ClaudeDesktopStrategy(),
        CursorProjectStrategy(),
        WindsurfStrategy(),
    ]

def install_mcp_server(server_name: str, command: str, args: list[str]) -> list[tuple[str, bool, str]]:
    """Install the MCP server across all discovered clients.
    
    Returns a list of (client_name, success, path_or_error_msg).
    """
    results = []
    strategies = get_strategies()
    for strategy in strategies:
        config_path = strategy.get_config_path()
        if not config_path:
            results.append((strategy.name, False, "Unsupported platform"))
            continue
            
        success, msg = strategy.inject_server(server_name, command, args)
        if success:
            results.append((strategy.name, True, msg))
        else:
            results.append((strategy.name, False, msg))
            
    return results
