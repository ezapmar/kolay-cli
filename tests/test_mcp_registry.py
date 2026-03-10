"""
tests/test_mcp_registry.py — Unit tests for services/mcp_registry.py.

Covers:
  - Base class MCPClientStrategy schema (_set_server for mcpServers)
  - VSCodeStrategy schema (uses "servers" key)
  - ZedStrategy schema (uses "context_servers" with nested path/args)
  - inject_server happy path: creates file + correct JSON written
  - inject_server: merges into existing config without destroying other keys
  - inject_server: malformed JSON aborts with error (destructive-write guard)
  - inject_server: path not determinable (False, "Unsupported platform")
  - inject_server: OS permission error (False, human error message)
  - _read_config: nonexistent file empty dict (creates fresh)
  - install_mcp_server: selected filter passes only chosen clients
  - install_mcp_server: selected=None installs all
  - get_strategies: returns 7 strategies with unique names
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kolay_cli.services.mcp_registry import (
    ClaudeDesktopStrategy,
    CursorGlobalStrategy,
    GeminiCLIStrategy,
    VSCodeStrategy,
    WindsurfStrategy,
    ZedStrategy,
    get_strategies,
    install_mcp_server,
)


# ── get_strategies registry ────────────────────────────────────────────────────

class TestGetStrategies:
    def test_returns_seven_strategies(self):
        strats = get_strategies()
        assert len(strats) == 7

    def test_all_names_are_unique(self):
        strats = get_strategies()
        names = [s.name for s in strats]
        assert len(names) == len(set(names)), "Duplicate strategy names found"

    def test_all_have_non_empty_name(self):
        for s in get_strategies():
            assert s.name, f"Strategy {type(s).__name__} has empty name"

    def test_all_have_non_empty_description(self):
        for s in get_strategies():
            assert s.description, f"Strategy {s.name} has empty description"


# ── Base schema (_set_server mcpServers) ─────────────────────────────────────

class TestBaseSchema:
    def test_set_server_creates_mcp_servers_key(self):
        s = ClaudeDesktopStrategy()
        data: dict = {}
        s._set_server(data, "kolay-ik", "/usr/bin/python", ["-m", "kolay"])
        assert "mcpServers" in data
        assert "kolay-ik" in data["mcpServers"]

    def test_set_server_writes_command_and_args(self):
        s = ClaudeDesktopStrategy()
        data: dict = {}
        s._set_server(data, "kolay-ik", "/usr/bin/python", ["-m", "kolay"])
        entry = data["mcpServers"]["kolay-ik"]
        assert entry["command"] == "/usr/bin/python"
        assert entry["args"] == ["-m", "kolay"]

    def test_set_server_preserves_existing_keys(self):
        s = ClaudeDesktopStrategy()
        data = {"mcpServers": {"other-tool": {"command": "npx", "args": []}}}
        s._set_server(data, "kolay-ik", "kolay", ["mcp", "serve"])
        assert "other-tool" in data["mcpServers"]
        assert "kolay-ik" in data["mcpServers"]

    def test_set_server_resets_corrupt_mcp_servers(self):
        """If mcpServers is not a dict, it should be reset rather than erroring."""
        s = ClaudeDesktopStrategy()
        data = {"mcpServers": "broken"}
        s._set_server(data, "kolay-ik", "kolay", [])
        assert isinstance(data["mcpServers"], dict)


# ── VSCode schema (uses "servers") ────────────────────────────────────────────

class TestVSCodeSchema:
    def test_uses_servers_key_not_mcp_servers(self):
        s = VSCodeStrategy()
        data: dict = {}
        s._set_server(data, "kolay-ik", "kolay", ["mcp", "serve"])
        assert "servers" in data
        assert "mcpServers" not in data

    def test_entry_has_command_and_args(self):
        s = VSCodeStrategy()
        data: dict = {}
        s._set_server(data, "kolay-ik", "kolay", ["mcp", "serve"])
        entry = data["servers"]["kolay-ik"]
        assert entry["command"] == "kolay"
        assert entry["args"] == ["mcp", "serve"]

    def test_entry_has_no_type_field(self):
        """VS Code infers stdio — we should not emit 'type': 'stdio'."""
        s = VSCodeStrategy()
        data: dict = {}
        s._set_server(data, "kolay-ik", "kolay", [])
        assert "type" not in data["servers"]["kolay-ik"]

    def test_preserves_existing_servers(self):
        s = VSCodeStrategy()
        data = {"servers": {"playwright": {"command": "npx", "args": ["-y", "@ms/playwright"]}}}
        s._set_server(data, "kolay-ik", "kolay", [])
        assert "playwright" in data["servers"]
        assert "kolay-ik" in data["servers"]


# ── Zed schema (uses "context_servers") ──────────────────────────────────────

class TestZedSchema:
    def test_uses_context_servers_key(self):
        s = ZedStrategy()
        data: dict = {}
        s._set_server(data, "kolay-ik", "/usr/bin/kolay", ["mcp", "serve"])
        assert "context_servers" in data

    def test_nested_command_structure(self):
        s = ZedStrategy()
        data: dict = {}
        s._set_server(data, "kolay-ik", "/usr/bin/kolay", ["mcp", "serve"])
        entry = data["context_servers"]["kolay-ik"]
        assert "command" in entry
        assert entry["command"]["path"] == "/usr/bin/kolay"
        assert entry["command"]["args"] == ["mcp", "serve"]


# ── inject_server happy path ───────────────────────────────────────────────────

class TestInjectServer:
    def test_creates_config_file(self, tmp_path):
        config_file = tmp_path / "claude_desktop_config.json"
        s = ClaudeDesktopStrategy()
        with patch.object(s, "get_config_path", return_value=config_file):
            ok, msg = s.inject_server("kolay-ik", "kolay", ["mcp", "serve"])
        assert ok is True
        assert config_file.exists()

    def test_written_json_is_valid(self, tmp_path):
        config_file = tmp_path / "config.json"
        s = ClaudeDesktopStrategy()
        with patch.object(s, "get_config_path", return_value=config_file):
            s.inject_server("kolay-ik", "kolay", ["mcp", "serve"])
        data = json.loads(config_file.read_text())
        assert "mcpServers" in data
        assert data["mcpServers"]["kolay-ik"]["command"] == "kolay"

    def test_merges_without_destroying_other_keys(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "globalShortcut": "Ctrl+Space",
            "mcpServers": {"other": {"command": "npx", "args": []}},
        }))
        s = ClaudeDesktopStrategy()
        with patch.object(s, "get_config_path", return_value=config_file):
            ok, _ = s.inject_server("kolay-ik", "kolay", ["mcp", "serve"])
        data = json.loads(config_file.read_text())
        assert data["globalShortcut"] == "Ctrl+Space"
        assert "other" in data["mcpServers"]
        assert "kolay-ik" in data["mcpServers"]

    def test_creates_parent_dirs(self, tmp_path):
        config_file = tmp_path / "deep" / "nested" / "config.json"
        s = ClaudeDesktopStrategy()
        with patch.object(s, "get_config_path", return_value=config_file):
            ok, _ = s.inject_server("kolay-ik", "kolay", [])
        assert ok is True
        assert config_file.exists()

    def test_new_file_starts_empty_dict(self, tmp_path):
        """A fresh (non-existent) config file is treated as {} and bootstrapped."""
        config_file = tmp_path / "fresh.json"
        s = ClaudeDesktopStrategy()
        with patch.object(s, "get_config_path", return_value=config_file):
            ok, _ = s.inject_server("kolay-ik", "kolay", [])
        assert ok is True
        data = json.loads(config_file.read_text())
        assert "mcpServers" in data

    def test_returns_config_path_string_on_success(self, tmp_path):
        config_file = tmp_path / "config.json"
        s = ClaudeDesktopStrategy()
        with patch.object(s, "get_config_path", return_value=config_file):
            ok, msg = s.inject_server("kolay-ik", "kolay", [])
        assert ok is True
        assert str(config_file) in msg


# ── Destructive-write guards ───────────────────────────────────────────────────

class TestDestructiveWriteGuard:
    def test_malformed_json_aborts(self, tmp_path):
        """Corrupt JSON in existing file must abort — not silently overwrite."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{this is not valid json!!!")
        s = ClaudeDesktopStrategy()
        with patch.object(s, "get_config_path", return_value=config_file):
            ok, msg = s.inject_server("kolay-ik", "kolay", [])
        assert ok is False
        assert "Invalid JSON" in msg or "data loss" in msg.lower()
        # Original file must be untouched
        assert config_file.read_text() == "{this is not valid json!!!"

    def test_permission_error_returns_false(self):
        """OS write error graceful (False, message), no exception raised."""
        # /root/... is guaranteed to be non-writable on macOS/Linux CI
        bad_path = Path("/root/cannot_create_this_dir/config.json")
        s = ClaudeDesktopStrategy()
        with patch.object(s, "get_config_path", return_value=bad_path):
            ok, msg = s.inject_server("kolay-ik", "kolay", [])
        assert ok is False
        assert msg  # some error description returned

    def test_no_config_path_returns_false(self):
        """If get_config_path() returns None, inject_server must return (False, ...)."""
        s = ClaudeDesktopStrategy()
        with patch.object(s, "get_config_path", return_value=None):
            ok, msg = s.inject_server("kolay-ik", "kolay", [])
        assert ok is False
        assert "platform" in msg.lower() or "not" in msg.lower()


# ── install_mcp_server — orchestrator ─────────────────────────────────────────

class TestInstallMCPServer:
    def test_selected_none_calls_all_strategies(self, tmp_path, monkeypatch):
        """selected=None all strategies are attempted."""
        from kolay_cli.services import mcp_registry

        calls = []

        class FakeStrategy:
            name = "Fake"
            def get_config_path(self):
                return tmp_path / "fake.json"
            def inject_server(self, *a):
                calls.append(self.name)
                return True, str(tmp_path / "fake.json")

        monkeypatch.setattr(mcp_registry, "get_strategies", lambda: [FakeStrategy()])
        results = install_mcp_server("kolay-ik", "kolay", [])
        assert len(results) == 1
        assert results[0][1] is True

    def test_selected_filters_strategies(self, tmp_path, monkeypatch):
        """Only the named strategy should run when selected is set."""
        from kolay_cli.services import mcp_registry

        class FakeA:
            name = "A"
            def get_config_path(self): return tmp_path / "a.json"
            def inject_server(self, *a): return True, str(tmp_path / "a.json")

        class FakeB:
            name = "B"
            def get_config_path(self): return tmp_path / "b.json"
            def inject_server(self, *a): raise AssertionError("B should not be called")

        monkeypatch.setattr(mcp_registry, "get_strategies", lambda: [FakeA(), FakeB()])
        results = install_mcp_server("kolay-ik", "kolay", [], selected=["A"])
        assert len(results) == 1
        assert results[0][0] == "A"

    def test_returns_list_of_triples(self, tmp_path, monkeypatch):
        from kolay_cli.services import mcp_registry

        class FakeStrategy:
            name = "Test"
            def get_config_path(self): return tmp_path / "t.json"
            def inject_server(self, *a): return True, str(tmp_path / "t.json")

        monkeypatch.setattr(mcp_registry, "get_strategies", lambda: [FakeStrategy()])
        results = install_mcp_server("kolay-ik", "kolay", [])
        assert isinstance(results, list)
        name, success, msg = results[0]
        assert isinstance(name, str)
        assert isinstance(success, bool)
        assert isinstance(msg, str)

    def test_no_config_path_skips_strategy(self, tmp_path, monkeypatch):
        """If a strategy returns None for get_config_path, it must be skipped (not crash)."""
        from kolay_cli.services import mcp_registry

        class NoPathStrategy:
            name = "NoPath"
            def get_config_path(self): return None
            def inject_server(self, *a): raise AssertionError("Should not be called")

        monkeypatch.setattr(mcp_registry, "get_strategies", lambda: [NoPathStrategy()])
        results = install_mcp_server("kolay-ik", "kolay", [])
        assert len(results) == 1
        assert results[0][1] is False
