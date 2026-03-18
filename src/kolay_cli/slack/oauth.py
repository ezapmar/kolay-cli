"""Slack OAuth install flow — "Add to Slack" button support."""
from __future__ import annotations

import os

from starlette.requests import Request
from starlette.responses import RedirectResponse, HTMLResponse, JSONResponse
from starlette.routing import Route


_SCOPES = "commands,chat:write,chat:write.public,files:write,channels:read"


def _callback_url(request: Request) -> str:
    """Build the OAuth callback URL, always using HTTPS.

    Behind a reverse proxy (Railway, Render, etc.) Starlette sees
    http:// internally. We fix this by:
      1. Using PUBLIC_URL env var if set (e.g. https://kolay.up.railway.app)
      2. Otherwise forcing the scheme to https on the auto-generated URL
    """
    public_url = os.environ.get("PUBLIC_URL", "").rstrip("/")
    if public_url:
        return f"{public_url}/slack/install/callback"

    # Fallback: use request.url_for but force https
    raw = str(request.url_for("install_callback"))
    return raw.replace("http://", "https://", 1)



def _client_id() -> str:
    v = os.environ.get("SLACK_CLIENT_ID", "")
    if not v:
        raise RuntimeError("SLACK_CLIENT_ID is not set.")
    return v


def _client_secret() -> str:
    v = os.environ.get("SLACK_CLIENT_SECRET", "")
    if not v:
        raise RuntimeError("SLACK_CLIENT_SECRET is not set.")
    return v


# ── Step 1: Redirect to Slack ────────────────────────────────────────────────

async def install_redirect(request: Request) -> RedirectResponse:
    """Redirect the browser to Slack's OAuth authorize page."""
    client_id = _client_id()
    redirect_uri = _callback_url(request)
    url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={client_id}"
        f"&scope={_SCOPES}"
        f"&redirect_uri={redirect_uri}"
    )
    return RedirectResponse(url)


# ── Step 2: Handle callback ──────────────────────────────────────────────────

async def install_callback(request: Request) -> HTMLResponse:
    """Exchange the OAuth code for a bot token, then show onboard form."""
    import httpx

    code = request.query_params.get("code")
    error = request.query_params.get("error")

    if error:
        return HTMLResponse(f"<h2>Installation cancelled</h2><p>{error}</p>", status_code=400)
    if not code:
        return HTMLResponse("<h2>Missing authorization code</h2>", status_code=400)

    # Exchange code → access token
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "code": code,
                "redirect_uri": _callback_url(request),
            },
        )
        data = resp.json()

    if not data.get("ok"):
        return HTMLResponse(
            f"<h2>OAuth failed</h2><pre>{data.get('error', 'unknown')}</pre>",
            status_code=400,
        )

    team_id = data["team"]["id"]
    team_name = data["team"]["name"]
    bot_token = data["access_token"]

    # Render the onboard form (Step 3)
    from .onboard import render_onboard_form
    return HTMLResponse(render_onboard_form(team_id, team_name, bot_token))


# ── Step 3: Save tenant ──────────────────────────────────────────────────────

async def install_complete(request: Request) -> HTMLResponse:
    """Receive the onboard form POST, save to TenantStore."""
    form = await request.form()

    team_id = str(form.get("team_id", ""))
    team_name = str(form.get("team_name", ""))
    bot_token = str(form.get("bot_token", ""))
    kolay_token = str(form.get("kolay_api_token", "")).strip()
    channels = str(form.get("allowed_channels", "")).strip()
    users = str(form.get("allowed_users", "")).strip()

    if not team_id or not bot_token or not kolay_token:
        return HTMLResponse("<h2>Missing required fields</h2>", status_code=400)

    from .tenant_store import Tenant, TenantStore
    store = TenantStore()
    store.upsert(Tenant(
        team_id=team_id,
        team_name=team_name,
        kolay_api_token=kolay_token,
        slack_bot_token=bot_token,
        allowed_channels=channels,
        allowed_users=users,
    ))

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head><title>Kolay IK — Installed</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 500px; margin: 60px auto; text-align: center; }}
        .check {{ font-size: 64px; }}
        code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }}
    </style>
    </head>
    <body>
        <div class="check">[OK]</div>
        <h2>Kolay IK installed to <strong>{team_name}</strong></h2>
        <p>Try <code>/kolay help</code> in Slack to get started.</p>
    </body>
    </html>
    """)


# ── Route collection ─────────────────────────────────────────────────────────

oauth_routes = [
    Route("/", endpoint=install_redirect, methods=["GET"]),
    Route("/callback", endpoint=install_callback, methods=["GET"], name="install_callback"),
    Route("/complete", endpoint=install_complete, methods=["POST"]),
]
