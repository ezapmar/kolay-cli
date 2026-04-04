"""Tests for package separation (platform.md §7.3).

Verifies that kolay_core and kolay_mcp are importable, expose the
correct public API, and provide clean error surfaces.
"""
from __future__ import annotations

import importlib
import sys

import pytest


# ── kolay_core ──────────────────────────────────────────────────────────────

class TestKolayCore:
    """Shared kernel package must expose the full public API."""

    def test_import_succeeds(self) -> None:
        import kolay_core
        assert hasattr(kolay_core, "__version__")

    def test_api_client_available(self) -> None:
        from kolay_core import KolayClient, safe_id, APIError, HTTP_ERRORS
        assert callable(KolayClient)
        assert callable(safe_id)

    def test_auth_exports(self) -> None:
        from kolay_core import require_auth, KOLAY_TOKEN_CTX
        assert callable(require_auth)

    def test_services_namespace(self) -> None:
        from kolay_core import services
        # Every service module listed in services/__init__.py must be accessible
        for name in ("person", "leave", "timelog", "training", "calendar"):
            assert hasattr(services, name), f"services.{name} missing"

    def test_services_person_callable(self) -> None:
        from kolay_core import services
        assert callable(getattr(services.person, "list_people", None))


# ── kolay_mcp ───────────────────────────────────────────────────────────────

class TestKolayMcp:
    """MCP server package must expose server, gateway, and marketplace APIs."""

    def test_import_succeeds(self) -> None:
        import kolay_mcp
        assert hasattr(kolay_mcp, "mcp")

    def test_mcp_server_instance(self) -> None:
        from kolay_mcp import mcp
        # FastMCP instance with registered tools
        assert hasattr(mcp, "run")

    def test_gateway_export(self) -> None:
        from kolay_mcp import register_gateway_middleware
        assert callable(register_gateway_middleware)

    def test_rag_exports(self) -> None:
        from kolay_mcp import inject_rag_context, retrieve_context
        assert callable(inject_rag_context)
        assert callable(retrieve_context)

    def test_marketplace_exports(self) -> None:
        from kolay_mcp import generate_manifest, PLATFORMS
        assert callable(generate_manifest)
        assert "openai" in PLATFORMS
        assert "anthropic" in PLATFORMS

    def test_generate_manifest_works(self) -> None:
        from kolay_mcp import generate_manifest
        m = generate_manifest("anthropic", "https://mcp.kolayik.com")
        assert m["schema_version"] == "v1"

    def test_http_app_factory(self) -> None:
        from kolay_mcp import create_secured_http_app
        assert callable(create_secured_http_app)

    def test_main_module_exists(self) -> None:
        """python -m kolay_mcp must work."""
        mod = importlib.import_module("kolay_mcp.__main__")
        assert hasattr(mod, "main")
        assert callable(mod.main)


# ── Cross-package consistency ───────────────────────────────────────────────

class TestCrossPackage:
    """Both packages must resolve to the same underlying objects."""

    def test_same_api_client(self) -> None:
        from kolay_core import KolayClient as Core
        from kolay_cli.api.client import KolayClient as Direct
        assert Core is Direct

    def test_same_mcp_server(self) -> None:
        from kolay_mcp import mcp as Facade
        from kolay_cli.mcp_server import mcp as Direct
        assert Facade is Direct

    def test_version_consistency(self) -> None:
        from kolay_core import __version__ as v_core
        from kolay_cli import __version__ as v_cli
        assert v_core == v_cli
