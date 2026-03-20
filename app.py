"""
Railway entry point — Universal Stateless MCP Proxy for Kolay IK.

Authentication is handled at the TOOL level via @require_auth, not at
the HTTP transport level.  This allows MCP clients (Mistral Le Chat,
OpenAI Desktop, Claude, etc.) to complete the protocol handshake before
any authentication is checked.

Token resolution (in priority order):
  1. X-Kolay-Token header   per-request token from client
  2. Authorization: Bearer   Mistral/OpenAI sends token this way
  3. KOLAY_API_TOKEN env var single-tenant fallback (Railway config)

The server is entirely stateless. Per-request tokens live only in a
ContextVar for the duration of the ASGI call and are immediately discarded.
No tokens, PII, or HR response data are ever logged or persisted.

Environment variables:
  KOLAY_API_TOKEN  – Kolay IK API token (required for single-tenant)
  MCP_API_KEY      – optional gatekeeper (extra abuse-prevention layer)
  PORT             – set by Railway automatically (default: 8080)
  PYTHONUNBUFFERED – set to 1 on Railway for immediate log output

Connection URL:
  https://<your-domain>/mcp
"""
from __future__ import annotations

import os
import sys
import warnings
from contextvars import ContextVar

# ── Silence upstream deprecation from websockets 16.x ──
warnings.filterwarnings("ignore", message="websockets.legacy is deprecated")
warnings.filterwarnings("ignore", message="websockets.server.WebSocketServerProtocol is deprecated")

# ── FastMCP log suppression (must be set before import) ──
os.environ.setdefault("FASTMCP_LOG_LEVEL", "WARNING")
os.environ.setdefault("FASTMCP_SHOW_SERVER_BANNER", "False")

import uvicorn  # noqa: E402

from kolay_cli.server_middleware import KolayProxyMiddleware

# ────────────────────────────────────────────────────────────────────
# MCP Server (validate_connection lives in mcp_server.py)
# ────────────────────────────────────────────────────────────────────
from kolay_cli.mcp_server import mcp  # noqa: E402


# ────────────────────────────────────────────────────────────────────
# App Factory + Startup
# ────────────────────────────────────────────────────────────────────
def create_proxy_app():
    """Build the ASGI app with token injection middleware."""
    starlette_app = mcp.http_app()
    mcp_proxy = KolayProxyMiddleware(starlette_app)
    return mcp_proxy


host = "0.0.0.0"
port = int(os.environ.get("PORT", 8080))
app = create_proxy_app()

if __name__ == "__main__":
    api_key = os.environ.get("MCP_API_KEY")
    kolay_token = os.environ.get("KOLAY_API_TOKEN")

    print(f"\nKolay IK MCP Proxy (Universal Stateless)", flush=True)
    print(f"  Endpoint:     http://{host}:{port}/mcp", flush=True)
    print(f"  Gatekeeper:   {'enabled' if api_key else 'disabled (tools still protected by @require_auth)'}", flush=True)
    print(f"  Kolay Token:  {'set via env' if kolay_token else 'not set (clients must send X-Kolay-Token)'}", flush=True)
    print(f"  Rate Limit:   {'enabled' if os.environ.get('MCP_RATE_LIMIT_ENABLED', '').lower() in ('1', 'true', 'yes') else 'disabled (set MCP_RATE_LIMIT_ENABLED=true)'}", flush=True)
    print(f"  Activity Log: always on (structured JSON to stdout)", flush=True)
    print("", flush=True)

    uvicorn.run(app, host=host, port=port)
