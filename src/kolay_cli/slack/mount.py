"""
Mount Slack Bolt (HTTP mode) onto the existing FastMCP Starlette app.

Architecture:
    kolay-mcp (uvicorn) ──► Starlette app
                               ├── /mcp          ← FastMCP (MCP protocol)
                               ├── /slack/events ← Slack Bolt HTTP handler
                               └── /slack/                       (same)

No Socket Mode. No separate process. One `uvicorn` instance handles both.

Usage:
    # Instead of `create_secured_http_app()` in mcp_server.py, use:
    from kolay_cli.slack.mount import create_combined_app
    uvicorn.run(create_combined_app(), host=host, port=port)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


# ── .env loader (same as standalone mode) ────────────────────────────────────

def _load_env() -> None:
    try:
        from dotenv import load_dotenv, find_dotenv
        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path, override=False)
    except ImportError:
        pass


# ── Slack Bolt HTTP app ───────────────────────────────────────────────────────

def _build_bolt_app():  # type: ignore[no-untyped-def]
    """Create the Slack Bolt App in HTTP mode (no socket mode)."""
    from slack_bolt import App
    from .dispatcher import (
        dispatch,
        handle_leave_request_submission,
        handle_timelog_create_submission,
    )
    from .quiz import handle_mode_selection, handle_answer
    from .modals import LEAVE_REQUEST_CALLBACK, TIMELOG_CREATE_CALLBACK

    signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
    bot_token = os.environ.get("SLACK_BOT_TOKEN")

    if not signing_secret:
        raise RuntimeError(
            "SLACK_SIGNING_SECRET is required for HTTP mode. "
            "Find it at api.slack.com/apps → Basic Information → Signing Secret."
        )
    if not bot_token:
        raise RuntimeError("SLACK_BOT_TOKEN is not set.")

    app = App(token=bot_token, signing_secret=signing_secret)

    @app.command("/kolay")
    def kolay_command(ack, body, client):  # type: ignore[no-untyped-def]
        dispatch(body.get("text", ""), body, client, ack)

    @app.view(LEAVE_REQUEST_CALLBACK)
    def leave_modal_submit(ack, body, client):  # type: ignore[no-untyped-def]
        handle_leave_request_submission(ack, body, client)

    @app.view(TIMELOG_CREATE_CALLBACK)
    def timelog_modal_submit(ack, body, client):  # type: ignore[no-untyped-def]
        handle_timelog_create_submission(ack, body, client)

    @app.action({"action_id": lambda aid: aid.startswith("quiz_start_mode_")})
    def quiz_mode_button(ack, body, client):  # type: ignore[no-untyped-def]
        handle_mode_selection(ack, body, client)

    @app.action({"action_id": lambda aid: aid.startswith("quiz_answer_")})
    def quiz_answer_button(ack, body, client):  # type: ignore[no-untyped-def]
        handle_answer(ack, body, client)

    return app


# ── Combined ASGI app ─────────────────────────────────────────────────────────

def create_combined_app():
    """
    Build one Starlette ASGI application that serves:
      • /mcp        — FastMCP (MCP protocol, with APIKeyMiddleware)
      • /slack/*    — Slack Bolt HTTP handler
    """
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from starlette.responses import JSONResponse
    from starlette.requests import Request

    # ── MCP sub-app (already has APIKeyMiddleware) ────────────────────────────
    from kolay_cli.mcp_server import create_secured_http_app
    mcp_asgi = create_secured_http_app()

    # ── Slack Bolt ASGI handler ───────────────────────────────────────────────
    from slack_bolt.async_app import AsyncApp
    from slack_bolt.adapter.starlette.async_handler import AsyncSlackRequestHandler

    # Build as async Bolt app (AsyncApp handles async ASGI properly)
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    bot_token = os.environ.get("SLACK_BOT_TOKEN", "")

    # Validate eagerly
    if not signing_secret:
        raise RuntimeError(
            "\n❌  SLACK_SIGNING_SECRET is not set.\n"
            "    Get it from: api.slack.com/apps → Basic Information → Signing Secret\n"
            "    Add it to your .env file and restart."
        )
    if not bot_token:
        raise RuntimeError(
            "\n❌  SLACK_BOT_TOKEN is not set.\n"
            "    Get it from: api.slack.com/apps → OAuth & Permissions → Bot User OAuth Token\n"
        )

    from .dispatcher import (
        dispatch,
        handle_leave_request_submission,
        handle_timelog_create_submission,
        _warn_partial_config,
    )
    from .quiz import handle_mode_selection, handle_answer
    from .modals import LEAVE_REQUEST_CALLBACK, TIMELOG_CREATE_CALLBACK

    _warn_partial_config()

    bolt_app = AsyncApp(token=bot_token, signing_secret=signing_secret)

    @bolt_app.command("/kolay")
    async def kolay_command(ack, body, client):  # type: ignore[no-untyped-def]
        dispatch(body.get("text", ""), body, client, ack)

    @bolt_app.view(LEAVE_REQUEST_CALLBACK)
    async def leave_modal_submit(ack, body, client):  # type: ignore[no-untyped-def]
        handle_leave_request_submission(ack, body, client)

    @bolt_app.view(TIMELOG_CREATE_CALLBACK)
    async def timelog_submit(ack, body, client):  # type: ignore[no-untyped-def]
        handle_timelog_create_submission(ack, body, client)

    @bolt_app.action({"action_id": lambda aid: aid.startswith("quiz_start_mode_")})
    async def quiz_mode(ack, body, client):  # type: ignore[no-untyped-def]
        handle_mode_selection(ack, body, client)

    @bolt_app.action({"action_id": lambda aid: aid.startswith("quiz_answer_")})
    async def quiz_answer(ack, body, client):  # type: ignore[no-untyped-def]
        handle_answer(ack, body, client)

    slack_handler = AsyncSlackRequestHandler(bolt_app)

    # ── Starlette route for all /slack/* requests ─────────────────────────────
    async def slack_endpoint(request: Request) -> Any:
        return await slack_handler.handle(request)

    # ── Health check ──────────────────────────────────────────────────────────
    async def health(request: Request) -> JSONResponse:
        from .dispatcher import _access_config
        allowed_ch, allowed_users = _access_config()
        return JSONResponse({
            "status": "ok",
            "services": {"mcp": True, "slack": True},
            "access_gate": {
                "active": bool(allowed_ch and allowed_users),
                "channels": len(allowed_ch),
                "users": len(allowed_users),
            },
        })

    app = Starlette(
        routes=[
            Mount("/mcp", app=mcp_asgi),
            Mount("/slack", app=Starlette(routes=[
                Mount("/", app=slack_endpoint),
            ])),
        ],
    )

    # Add health at root level
    from starlette.routing import Route
    app.routes.insert(0, Route("/health", health))

    return app


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """
    Run the combined MCP + Slack server with uvicorn.
    Replaces both `kolay-mcp` (HTTP mode) and `kolay-slack` with a single process.
    """
    _load_env()

    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))

    _startup_banner(host, port)

    app = create_combined_app()
    uvicorn.run(app, host=host, port=port)


def _startup_banner(host: str, port: int) -> None:
    from .dispatcher import _access_config
    allowed_ch, allowed_users = _access_config()
    gate = (
        f"✅  Option C active ({len(allowed_ch)} channel(s), {len(allowed_users)} user(s))"
        if (allowed_ch and allowed_users)
        else "⚠️  Access gate inactive (set both ALLOWED_CHANNEL_IDS + ALLOWED_USER_IDS)"
    )
    print("\n╔══════════════════════════════════════════════════╗")
    print("║   ⚡️  Kolay IK — Combined MCP + Slack Server    ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"  🌐  http://{host}:{port}")
    print(f"  📡  MCP endpoint  → http://{host}:{port}/mcp")
    print(f"  💬  Slack events  → http://{host}:{port}/slack/events")
    print(f"  🏥  Health check  → http://{host}:{port}/health")
    print(f"  🔐  Access control: {gate}\n")
