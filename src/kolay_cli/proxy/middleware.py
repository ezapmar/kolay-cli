"""Shared ASGI Middleware for the Kolay MCP Server."""
from __future__ import annotations

import os
from contextvars import ContextVar
from typing import Any



def _log(msg: str) -> None:
    """Print a log line with immediate flush (required for containers)."""
    print(msg, flush=True)

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

    def __init__(self, app: Any):
        self.app = app
        raw_key = os.environ.get("MCP_API_KEY")
        self.api_key = raw_key.strip() if raw_key else None

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
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
                
                # Fallback: query string for clients without custom header support (ChatGPT)
                if not x_api_key:
                    query_string = scope.get("query_string", b"").decode()
                    if query_string:
                        from urllib.parse import parse_qs
                        qs = parse_qs(query_string)
                        if "api_key" in qs:
                            x_api_key = qs["api_key"][0]
                        elif "apikey" in qs:
                            x_api_key = qs["apikey"][0]

                if x_api_key and x_api_key == self.api_key:
                    pass  # success internally log if wanted
                elif x_api_key:
                    _log(f"[auth] Gatekeeper: key mismatch (len={len(x_api_key)} vs expected={len(self.api_key)})")
                    if scope["type"] == "http":
                        await self._send_json(send, 401, {
                            "error": "Unauthorized",
                            "message": "Invalid X-API-Key.",
                        })
                    else:
                        await send({"type": "websocket.close", "code": 4001})
                    return
                # If no X-API-Key header at all, let it through --
                # the gatekeeper is a bonus layer, not a hard requirement.
                # Tool-level @require_auth is the real security.

        # ── Token Injection (Kolay API Token) ──
        kolay_token = self._extract_token(headers, scope)
        
        # Setup specific ContextVar for Kolay
        from .auth import KOLAY_TOKEN_CTX
        token_reset = KOLAY_TOKEN_CTX.set(kolay_token)
        
        try:
            await self.app(scope, receive, send)
        finally:
            KOLAY_TOKEN_CTX.reset(token_reset)

    @staticmethod
    def _extract_token(headers: dict[bytes, bytes], scope: dict[str, Any] | None = None) -> str | None:
        """Extract the Kolay IK API token from headers or query string.

        1. X-Kolay-Token: <token> (explicit, preferred)
        2. Authorization: Bearer <token> (Mistral/OpenAI standard)
        3. ?token=<token> query string (ChatGPT MCP Beta -- no custom header support)
        """
        kolay = headers.get(b"x-kolay-token", b"").decode().strip()
        if kolay:
            return kolay

        auth = headers.get(b"authorization", b"").decode().strip()
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()

        # Fallback: query string for clients that cannot send custom headers (ChatGPT)
        if scope:
            query_string = scope.get("query_string", b"").decode()
            if query_string:
                from urllib.parse import parse_qs
                qs = parse_qs(query_string)
                if "token" in qs:
                    return qs["token"][0]

        return None

    @staticmethod
    async def _send_json(send: Any, status: int, body_dict: dict[str, Any]) -> None:
        import json
        body = json.dumps(body_dict).encode()
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
                [b"cache-control", b"no-store"],
            ],
        })
        await send({"type": "http.response.body", "body": body})
