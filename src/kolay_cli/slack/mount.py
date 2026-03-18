"""
Mount Slack Bolt (HTTP mode) + OAuth onto the existing FastMCP Starlette app.

Architecture:
    kolay-combined (uvicorn)
    ├── /mcp              ← FastMCP (MCP protocol, with APIKeyMiddleware)
    ├── /slack/events     ← Slack Bolt HTTP handler (multi-tenant via middleware)
    ├── /slack/install    ← OAuth "Add to Slack" flow
    ├── /health           ← JSON status check
    └── /                 ← Landing page with "Add to Slack" button

Multi-tenant: each Slack workspace gets its own Kolay token via TenantStore.
No Socket Mode. One process. One port.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


# ── .env loader ───────────────────────────────────────────────────────────────

def _load_env() -> None:
    try:
        from dotenv import load_dotenv, find_dotenv
        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path, override=False)
    except ImportError:
        pass


# ── Combined ASGI app ─────────────────────────────────────────────────────────

def create_combined_app():  # type: ignore[no-untyped-def]
    """
    Build one Starlette ASGI application that serves:
      • /mcp              — FastMCP (MCP protocol, with APIKeyMiddleware)
      • /slack/events     — Slack Bolt HTTP handler (multi-tenant)
      • /slack/install    — OAuth install flow + onboard form
      • /health           — JSON health check
    """
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route
    from starlette.requests import Request
    from starlette.responses import JSONResponse, HTMLResponse

    # ── MCP sub-app ───────────────────────────────────────────────────────────
    from kolay_cli.mcp_server import create_secured_http_app
    mcp_asgi = create_secured_http_app()

    # ── Tenant store ──────────────────────────────────────────────────────────
    from .tenant_store import TenantStore
    store = TenantStore()

    # ── Slack Bolt app (HTTP mode, multi-tenant) ──────────────────────────────
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    if not signing_secret:
        raise RuntimeError(
            "\n❌  SLACK_SIGNING_SECRET is not set.\n"
            "    Get it from: api.slack.com/apps → Basic Information → Signing Secret\n"
        )

    from slack_bolt import App as BoltApp
    from slack_bolt.adapter.starlette import SlackRequestHandler

    from .dispatcher import (
        dispatch,
        handle_leave_request_submission,
        handle_timelog_create_submission,
        _warn_partial_config,
    )
    from .quiz import handle_mode_selection, handle_answer
    from .modals import LEAVE_REQUEST_CALLBACK, TIMELOG_CREATE_CALLBACK
    from .middleware import tenant_middleware, set_store

    # Share store with middleware
    set_store(store)
    _warn_partial_config()

    # In multi-tenant mode we can't set a fixed bot_token at init —
    # the middleware resolves the correct token per request.
    # We pass a dummy token here; Bolt requires it at init but the
    # per-workspace token is looked up by the middleware on each request.
    bolt_app = BoltApp(
        signing_secret=signing_secret,
        token=os.environ.get("SLACK_BOT_TOKEN", "xoxb-not-used"),
        # We register the tenant middleware to run before all handlers
    )

    bolt_app.use(tenant_middleware)

    @bolt_app.command("/kolay")
    def kolay_command(ack, body, client):  # type: ignore[no-untyped-def]
        dispatch(body.get("text", ""), body, client, ack)

    @bolt_app.view(LEAVE_REQUEST_CALLBACK)
    def leave_modal_submit(ack, body, client):  # type: ignore[no-untyped-def]
        handle_leave_request_submission(ack, body, client)

    @bolt_app.view(TIMELOG_CREATE_CALLBACK)
    def timelog_submit(ack, body, client):  # type: ignore[no-untyped-def]
        handle_timelog_create_submission(ack, body, client)

    @bolt_app.action({"action_id": lambda aid: aid.startswith("quiz_start_mode_")})
    def quiz_mode(ack, body, client):  # type: ignore[no-untyped-def]
        handle_mode_selection(ack, body, client)

    @bolt_app.action({"action_id": lambda aid: aid.startswith("quiz_answer_")})
    def quiz_answer(ack, body, client):  # type: ignore[no-untyped-def]
        handle_answer(ack, body, client)

    slack_handler = SlackRequestHandler(bolt_app)

    # ── Starlette route for Slack events ──────────────────────────────────────
    async def slack_events(request: Request) -> Any:
        return await slack_handler.handle(request)

    # ── OAuth routes ──────────────────────────────────────────────────────────
    from .oauth import oauth_routes

    # ── Health check ──────────────────────────────────────────────────────────
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({
            "status": "ok",
            "services": {"mcp": True, "slack": True},
            "tenants": store.count(),
        })

    # ── Landing page with "Add to Slack" ──────────────────────────────────────
    async def landing(request: Request) -> HTMLResponse:
        client_id = os.environ.get("SLACK_CLIENT_ID", "")
        install_url = f"/slack/install" if client_id else "#"
        tenant_count = store.count()
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head><title>Kolay IK</title>
        <style>
            body {{
                font-family: -apple-system, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                text-align: center;
            }}
            .card {{
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 48px;
                max-width: 440px;
            }}
            h1 {{ font-size: 36px; margin-bottom: 12px; }}
            p {{ font-size: 16px; opacity: 0.9; margin-bottom: 28px; }}
            a.btn {{
                display: inline-block;
                background: white;
                color: #667eea;
                padding: 14px 32px;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 700;
                font-size: 16px;
                transition: transform 0.15s;
            }}
            a.btn:hover {{ transform: scale(1.05); }}
            .stat {{ font-size: 13px; opacity: 0.7; margin-top: 20px; }}
        </style>
        </head>
        <body>
            <div class="card">
                <h1>🔷 Kolay IK</h1>
                <p>HR intelligence for Slack — people, leave, quiz, and more.</p>
                <a class="btn" href="{install_url}">Add to Slack</a>
                <p class="stat">{tenant_count} workspace{'s' if tenant_count != 1 else ''} connected</p>
            </div>
        </body>
        </html>
        """)

    # ── Assemble ──────────────────────────────────────────────────────────────
    app = Starlette(routes=[
        Route("/", landing),
        Route("/health", health),
        Mount("/mcp", app=mcp_asgi),
        Route("/slack/events", slack_events, methods=["POST"]),
        Mount("/slack/install", routes=oauth_routes),
    ])

    return app


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """Run the combined MCP + Slack server with uvicorn."""
    _load_env()

    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))

    _startup_banner(host, port)

    app = create_combined_app()
    uvicorn.run(app, host=host, port=port)


def _startup_banner(host: str, port: int) -> None:
    from .tenant_store import TenantStore
    try:
        store = TenantStore()
        tenant_count = store.count()
    except Exception:
        tenant_count = 0

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║   ⚡️  Kolay IK — Combined MCP + Slack Server        ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"  🌐  http://{host}:{port}")
    print(f"  📡  MCP endpoint    → /mcp")
    print(f"  💬  Slack events    → /slack/events")
    print(f"  🔗  Add to Slack    → /slack/install")
    print(f"  🏥  Health check    → /health")
    print(f"  🏢  Tenants: {tenant_count} workspace(s) connected\n")


if __name__ == "__main__":
    main()
