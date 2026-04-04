"""kolay-mcp — standalone MCP server for Kolay IK.

Deployable as a marketplace endpoint (OpenAI, Anthropic, Open WebUI)
or self-hosted gateway. Decoupled from the CLI at the package level —
same underlying code, clean entry surface.

Usage:
    python -m kolay_mcp                          # stdio (local AI client)
    python -m kolay_mcp --transport http          # HTTP (network deploy)
    kolay-mcp                                     # entry point (stdio)

Architecture (platform.md §7.3):
    Layer 1 — Gateway   (gateway.py)   rate limiting, metering, auth
    Layer 2 — RAG       (rag.py)       corporate memory injection
    Layer 3 — Tools     (server.py)    53 HR tools + prompts + resources
"""
from __future__ import annotations

import sys as _sys


def _dependency_check() -> None:
    """Fail fast with a helpful message if core deps are missing."""
    missing: list[str] = []
    for mod in ("fastmcp", "kolay_cli"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)

    if missing:
        print(
            f"\n"
            f"  kolay-mcp: missing dependencies: {', '.join(missing)}\n"
            f"\n"
            f"  Fix:\n"
            f"    pip install kolay-cli          # includes everything\n"
            f"    pip install kolay-cli[rag]     # + corporate memory\n"
            f"\n",
            file=_sys.stderr,
        )
        _sys.exit(1)


_dependency_check()

# ── Public re-exports ─────────────────────────────────────────────────────────
from kolay_cli.mcp_server import mcp, create_secured_http_app, APIKeyMiddleware  # noqa: E402
from kolay_cli.mcp.gateway import register_gateway_middleware  # noqa: E402
from kolay_cli.mcp.rag import inject_rag_context, retrieve_context  # noqa: E402
from kolay_cli.mcp.marketplace import generate_manifest, PLATFORMS  # noqa: E402

__all__ = [
    # server
    "mcp", "create_secured_http_app", "APIKeyMiddleware",
    # gateway
    "register_gateway_middleware",
    # rag
    "inject_rag_context", "retrieve_context",
    # marketplace
    "generate_manifest", "PLATFORMS",
]
