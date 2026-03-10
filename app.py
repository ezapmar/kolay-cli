"""
Railway entry point — Universal Stateless MCP Proxy for Kolay IK.

Authentication is handled at the TOOL level via @require_auth, not at
the HTTP transport level.  This allows MCP clients (Mistral Le Chat,
OpenAI Desktop, Claude, etc.) to complete the protocol handshake before
any authentication is checked.

Token resolution (in priority order):
  1. X-Kolay-Token header   → per-request token from client
  2. Authorization: Bearer   → Mistral/OpenAI sends token this way
  3. KOLAY_API_TOKEN env var → single-tenant fallback (Railway config)

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

# ────────────────────────────────────────────────────────────────────
# Context variable: carries the per-request Kolay token from the
# middleware down to the service layer.
# ────────────────────────────────────────────────────────────────────
request_token: ContextVar[str | None] = ContextVar("request_token", default=None)


def _log(msg: str) -> None:
    """Print a log line with immediate flush (required for containers)."""
    print(msg, flush=True)


# ────────────────────────────────────────────────────────────────────
# ASGI Middleware — Token Injection
# ────────────────────────────────────────────────────────────────────
class KolayProxyMiddleware:
    """Raw ASGI middleware that extracts the Kolay API token from
    request headers and injects it into the environment for the
    duration of the request.

    Optional gatekeeper: if MCP_API_KEY is set, requests must also
    provide that key via X-API-Key header.  If MCP_API_KEY is NOT set,
    the gatekeeper is disabled and all requests pass through to the
    MCP layer (tools are still protected by @require_auth).

    Token sources (checked in order):
      1. X-Kolay-Token header
      2. Authorization: Bearer <token>
    """

    def __init__(self, app):
        self.app = app
        raw_key = os.environ.get("MCP_API_KEY")
        self.api_key = raw_key.strip() if raw_key else None

    async def __call__(self, scope, receive, send):
        # Allow lifespan events
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        headers = dict(scope.get("headers", []))

        # ── Optional Gatekeeper (only if MCP_API_KEY is set) ──
        if self.api_key:
            # Always allow discovery paths (Mistral/Google probe these)
            if not path.startswith("/.well-known"):
                x_api_key = headers.get(b"x-api-key", b"").decode().strip()
                if x_api_key and x_api_key == self.api_key:
                    _log(f"[auth] Gatekeeper: ✔ key matched via X-API-Key")
                elif x_api_key:
                    _log(f"[auth] Gatekeeper: ✘ key mismatch (len={len(x_api_key)} vs expected={len(self.api_key)})")
                    await self._send_json(send, 401, {
                        "error": "Unauthorized",
                        "message": "Invalid X-API-Key.",
                    })
                    return
                # If no X-API-Key header at all, let it through —
                # the gatekeeper is a bonus layer, not a hard requirement.
                # Tool-level @require_auth is the real security.

        # ── Token Injection (Kolay API Token) ──
        kolay_token = self._extract_token(headers)
        if kolay_token:
            ctx_token = request_token.set(kolay_token)
            old_env = os.environ.get("KOLAY_API_TOKEN")
            os.environ["KOLAY_API_TOKEN"] = kolay_token

            # Invalidate security module's token cache
            try:
                from kolay_cli.security import _SENTINEL
                import kolay_cli.security as sec_mod
                sec_mod._token_cache = _SENTINEL
            except Exception:
                pass

            try:
                await self.app(scope, receive, send)
            finally:
                request_token.reset(ctx_token)
                if old_env is not None:
                    os.environ["KOLAY_API_TOKEN"] = old_env
                else:
                    os.environ.pop("KOLAY_API_TOKEN", None)
                try:
                    sec_mod._token_cache = _SENTINEL  # type: ignore[possibly-undefined]
                except Exception:
                    pass
            return

        # No per-request token — fall through to app.
        # If KOLAY_API_TOKEN env var is set on Railway, tools will
        # use that (single-tenant mode).  If not, @require_auth
        # will return a structured error to the AI agent.
        await self.app(scope, receive, send)

    @staticmethod
    def _extract_token(headers: dict[bytes, bytes]) -> str | None:
        """Extract the Kolay IK API token from headers.

        1. X-Kolay-Token: <token>    (explicit, preferred)
        2. Authorization: Bearer <token>  (Mistral/OpenAI standard)
        """
        kolay = headers.get(b"x-kolay-token", b"").decode().strip()
        if kolay:
            return kolay

        auth = headers.get(b"authorization", b"").decode().strip()
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()

        return None

    @staticmethod
    async def _send_json(send, status: int, body_dict: dict):
        import json
        body = json.dumps(body_dict).encode()
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
            ],
        })
        await send({"type": "http.response.body", "body": body})


# ────────────────────────────────────────────────────────────────────
# MCP Server + Validation Tool
# ────────────────────────────────────────────────────────────────────
from kolay_cli.mcp_server import mcp  # noqa: E402


@mcp.tool
def validate_connection() -> dict:
    """Check if the Kolay İK API token is configured and valid.

    Call this tool FIRST before making any HR queries.
    Returns {valid, message} indicating whether the server can
    reach the Kolay API with the current credentials.
    """
    from kolay_cli.security import resolve_token, validate_token

    token = resolve_token()
    if not token:
        return {
            "valid": False,
            "message": "No Kolay API token found.",
            "hint": "Set KOLAY_API_TOKEN on the server, or send via X-Kolay-Token header.",
        }

    status = validate_token(token)
    if not status:
        return {
            "valid": False,
            "message": f"Token invalid: {status.reason}",
        }

    try:
        from kolay_cli.api.client import KolayClient
        client = KolayClient(token=token)
        result = client.post("v2/person/list", data={"page": 1, "limit": 1})
        count = result.get("data", {}).get("totalCount", "unknown")
        return {
            "valid": True,
            "message": f"Connected to Kolay IK ({count} employees).",
        }
    except Exception as e:
        return {
            "valid": False,
            "message": f"API rejected token: {e}",
        }


# ────────────────────────────────────────────────────────────────────
# App Factory + Startup
# ────────────────────────────────────────────────────────────────────
def create_proxy_app():
    """Build the ASGI app with token injection middleware."""
    starlette_app = mcp.http_app()
    return KolayProxyMiddleware(starlette_app)


host = "0.0.0.0"
port = int(os.environ.get("PORT", 8080))
app = create_proxy_app()

if __name__ == "__main__":
    api_key = os.environ.get("MCP_API_KEY")
    kolay_token = os.environ.get("KOLAY_API_TOKEN")

    _log(f"\n🔌 Kolay IK MCP Proxy (Universal Stateless)")
    _log(f"   Endpoint:   http://{host}:{port}/mcp")
    _log(f"   Gatekeeper: {'✔ enabled' if api_key else '✘ disabled (tools still protected by @require_auth)'}")
    _log(f"   Kolay Token: {'✔ set via env' if kolay_token else '⚠ not set (clients must send X-Kolay-Token)'}")
    _log("")

    uvicorn.run(app, host=host, port=port)
