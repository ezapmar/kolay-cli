"""kolay-core — shared kernel for all Kolay IK integrations.

This is the foundation package. Both the CLI (kolay-cli) and the MCP
server (kolay-mcp) import from here. If you're building a custom
integration, start here.

Quick start:
    from kolay_core import KolayClient, APIError
    from kolay_core import services

    client = KolayClient()
    people = services.person.list_people(limit=10)

Architecture (platform.md §7.3):
    kolay-core  = API client + auth + services + proxy security
    kolay-cli   = Typer CLI commands (depends on kolay-core)
    kolay-mcp   = FastMCP server + gateway + RAG (depends on kolay-core)
"""
from __future__ import annotations

# ── API Client ────────────────────────────────────────────────────────────────
from kolay_cli.api.client import KolayClient, safe_id
from kolay_cli.api.errors import APIError, HTTP_ERRORS

# ── Auth & Security ───────────────────────────────────────────────────────────
from kolay_cli.security import (
    require_auth,
    KOLAY_TOKEN_CTX,
)

# ── Services (business logic layer) ──────────────────────────────────────────
from kolay_cli import services  # noqa: F401 — namespace re-export

# ── Version ───────────────────────────────────────────────────────────────────
from kolay_cli import __version__

__all__ = [
    # api
    "KolayClient", "safe_id", "APIError", "HTTP_ERRORS",
    # auth
    "require_auth", "KOLAY_TOKEN_CTX",
    # services
    "services",
    # meta
    "__version__",
]
