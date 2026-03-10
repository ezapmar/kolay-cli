"""
Railway entry point — Universal Stateless MCP Proxy for Kolay IK.

Two-layer authentication:
  1. Gatekeeper:  X-API-Key header  →  validated against MCP_API_KEY env var
  2. Data Key:    X-Kolay-Token  or  Authorization: Bearer <token>
                  →  forwarded per-request to the Kolay IK API

The server is entirely stateless. Tokens are held in-memory for the
duration of a single request cycle and immediately discarded.

No tokens, PII, or HR response data are ever logged or persisted.

Environment variables:
  MCP_API_KEY      – gatekeeper secret   (required)
  PORT             – set by Railway      (default: 8080)

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

# ── FastMCP log suppression (must be set before import) ──
os.environ.setdefault("FASTMCP_LOG_LEVEL", "WARNING")
os.environ.setdefault("FASTMCP_SHOW_SERVER_BANNER", "False")

import uvicorn  # noqa: E402
from fastmcp import FastMCP  # noqa: E402

# ────────────────────────────────────────────────────────────────────
# Context variable: carries the per-request Kolay token from the
# middleware down to the service layer.  Automatically cleaned up
# when the ASGI task ends (no manual teardown needed).
# ────────────────────────────────────────────────────────────────────
request_token: ContextVar[str | None] = ContextVar("request_token", default=None)


# ────────────────────────────────────────────────────────────────────
# ASGI Middleware — Two-Layer Authentication
# ────────────────────────────────────────────────────────────────────
class ProxyAuthMiddleware:
    """Raw ASGI middleware implementing the universal proxy auth model.

    Layer 1 — Gatekeeper:
        Validates X-API-Key against MCP_API_KEY env var.

    Layer 2 — Data Key:
        Extracts the user's Kolay token from X-Kolay-Token or
        Authorization: Bearer headers and injects it into the
        request_token ContextVar for downstream services.

    Zero-persistence: tokens live only in the ContextVar for the
    duration of the ASGI call and are never logged.
    """

    def __init__(self, app):
        self.app = app
        self.api_key = os.environ.get("MCP_API_KEY")

    async def __call__(self, scope, receive, send):
        # Only gate HTTP requests (not lifespan events)
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))

        # ── Layer 1: Gatekeeper ──
        if self.api_key:
            provided_key = headers.get(b"x-api-key", b"").decode()
            if provided_key != self.api_key:
                if scope["type"] == "http":
                    await self._send_json(send, 401, {
                        "error": "Unauthorized",
                        "message": "Missing or invalid X-API-Key header.",
                        "hint": "Add the X-API-Key header with your server's MCP_API_KEY value.",
                    })
                    return
                await send({"type": "websocket.close", "code": 4001})
                return

        # ── Layer 2: Data Key (Kolay Token) ──
        kolay_token = self._extract_kolay_token(headers)
        if kolay_token:
            # Inject into the KOLAY_API_TOKEN env var so that
            # KolayClient() picks it up through the existing
            # config.get_api_token() → resolve_token() chain.
            # We use contextvars + env override for maximum compat.
            token = request_token.set(kolay_token)
            old_env = os.environ.get("KOLAY_API_TOKEN")
            os.environ["KOLAY_API_TOKEN"] = kolay_token

            # Invalidate the security module's token cache so it
            # re-reads from the env var on next resolve_token() call.
            try:
                from kolay_cli.security import _SENTINEL
                import kolay_cli.security as sec_mod
                sec_mod._token_cache = _SENTINEL
            except Exception:
                pass

            try:
                await self.app(scope, receive, send)
            finally:
                # ── Zero-persistence cleanup ──
                request_token.reset(token)
                if old_env is not None:
                    os.environ["KOLAY_API_TOKEN"] = old_env
                else:
                    os.environ.pop("KOLAY_API_TOKEN", None)
                # Re-invalidate cache after cleanup
                try:
                    sec_mod._token_cache = _SENTINEL  # type: ignore[possibly-undefined]
                except Exception:
                    pass
            return

        # No Kolay token provided — still allow the request through.
        # The MCP tools' @require_auth decorator will return a
        # structured 401 error to the AI agent, which is the correct
        # MCP-level response (not an HTTP 401).
        await self.app(scope, receive, send)

    @staticmethod
    def _extract_kolay_token(headers: dict[bytes, bytes]) -> str | None:
        """Extract the Kolay token from X-Kolay-Token or Authorization: Bearer."""
        # Prefer explicit X-Kolay-Token header
        kolay_header = headers.get(b"x-kolay-token", b"").decode().strip()
        if kolay_header:
            return kolay_header

        # Fall back to Authorization: Bearer <token>
        auth_header = headers.get(b"authorization", b"").decode().strip()
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()

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
    """Check if the user has provided a valid Kolay İK API token.

    Call this tool FIRST before making any HR queries. It confirms that
    the authentication chain (X-API-Key + X-Kolay-Token) is working
    correctly and the token is accepted by the Kolay API.

    Returns a status dict with {valid, message, token_type}.
    """
    from kolay_cli.security import resolve_token, validate_token

    token = resolve_token()
    if not token:
        return {
            "valid": False,
            "message": "No Kolay API token found in request headers.",
            "hint": "Send your Kolay token via X-Kolay-Token or Authorization: Bearer header.",
        }

    status = validate_token(token)
    if not status:
        return {
            "valid": False,
            "message": f"Token validation failed: {status.reason}",
            "hint": "Check that your token is correct and not expired.",
        }

    # Quick API ping to verify the token works end-to-end
    try:
        from kolay_cli.api.client import KolayClient
        client = KolayClient(token=token)
        result = client.post("v2/person/list", data={"page": 1, "limit": 1})
        employee_count = result.get("data", {}).get("totalCount", "unknown")
        return {
            "valid": True,
            "message": f"Token is valid. Connected to Kolay IK ({employee_count} employees).",
            "token_type": "JWT" if "." in token else "opaque",
        }
    except Exception as e:
        return {
            "valid": False,
            "message": f"Token accepted locally but API rejected it: {e}",
            "hint": "The token may have been revoked. Generate a new one at app.kolayik.com.",
        }


# ────────────────────────────────────────────────────────────────────
# App Factory
# ────────────────────────────────────────────────────────────────────
def create_proxy_app():
    """Build the secured ASGI app with two-layer auth middleware."""
    starlette_app = mcp.http_app()
    return ProxyAuthMiddleware(starlette_app)


# ── Enforce MCP_API_KEY — refuse to start without it ──
api_key = os.environ.get("MCP_API_KEY")
if not api_key:
    print(
        "\n❌ FATAL: MCP_API_KEY environment variable is not set.\n"
        "   The server refuses to start without a gatekeeper key.\n"
        "   Set it in your Railway dashboard: Settings → Variables → MCP_API_KEY\n"
    )
    sys.exit(1)

host = "0.0.0.0"
port = int(os.environ.get("PORT", 8080))
app = create_proxy_app()

if __name__ == "__main__":
    print(f"\n🔌 Kolay IK MCP Proxy (Universal Stateless)")
    print(f"   Endpoint:   http://{host}:{port}/mcp")
    print(f"   Gatekeeper: ✔ enabled (X-API-Key)")
    print(f"   Data Key:   X-Kolay-Token  or  Authorization: Bearer")
    print(f"   Key hint:   {api_key[:4]}...{api_key[-4:]}\n")
    uvicorn.run(app, host=host, port=port)
