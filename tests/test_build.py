"""Tests for build.py — PyInstaller build script."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


class TestBuildConfig:
    """Verify PyInstaller configuration values."""

    def test_entry_point_exists(self):
        from build import ENTRY_POINT
        assert ENTRY_POINT.exists(), f"Entry point {ENTRY_POINT} does not exist"

    def test_exe_name_is_set(self):
        from build import EXE_NAME
        assert EXE_NAME == "kolay-setup"

    def test_hidden_imports_include_keyring(self):
        from build import _hidden_imports
        imports = _hidden_imports()
        assert "keyring.backends" in imports

    def test_hidden_imports_include_fastmcp(self):
        from build import _hidden_imports
        imports = _hidden_imports()
        assert "fastmcp" in imports

    def test_hidden_imports_include_core(self):
        from build import _hidden_imports
        imports = _hidden_imports()
        assert "core.constants" in imports

    def test_hidden_imports_include_security(self):
        from build import _hidden_imports
        imports = _hidden_imports()
        assert "kolay_cli.security" in imports

    def test_hidden_imports_include_mcp_registry(self):
        from build import _hidden_imports
        imports = _hidden_imports()
        assert "kolay_cli.services.mcp_registry" in imports

    def test_build_function_exists(self):
        from build import build
        assert callable(build)
