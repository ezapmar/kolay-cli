"""Slack Bolt middleware: inject per-tenant Kolay token into KOLAY_TOKEN_CTX."""
from __future__ import annotations

from typing import Any

from ..security import KOLAY_TOKEN_CTX
from .tenant_store import TenantStore


# Module-level store — initialised lazily on first use.
_store: TenantStore | None = None


def _get_store() -> TenantStore:
    global _store
    if _store is None:
        _store = TenantStore()
    return _store


def set_store(store: TenantStore) -> None:
    """Allow external code (e.g. mount.py) to inject a shared store instance."""
    global _store
    _store = store


def tenant_middleware(payload: dict, body: dict, next: Any, client: Any = None) -> None:
    """Slack Bolt global middleware.

    Runs before every slash-command / action / view-submission handler.
    1. Extracts ``team_id`` from the Slack payload.
    2. Looks up the tenant in the store.
    3. Sets ``KOLAY_TOKEN_CTX`` so all downstream ``services.*`` calls
       use the correct company's Kolay API token.
    4. Overrides access-control env vars for the tenant.
    """
    team_id = (
        body.get("team_id")
        or (body.get("team") or {}).get("id")
        or ""
    )

    store = _get_store()
    tenant = store.find(team_id) if team_id else None

    if tenant is None:
        # Unknown workspace — bail with a friendly message
        if client:
            channel = body.get("channel_id") or body.get("channel", {}).get("id", "")
            user = body.get("user_id") or body.get("user", {}).get("id", "")
            if channel and user:
                client.chat_postEphemeral(
                    channel=channel,
                    user=user,
                    text=(
                        ":warning: This Slack workspace isn't connected to Kolay IK yet.\n"
                        "Ask your admin to visit the install page to set it up."
                    ),
                )
        return  # don't call next() — stop the chain

    # Inject tenant's Kolay token into the request-scoped ContextVar
    token = KOLAY_TOKEN_CTX.set(tenant.kolay_api_token)

    # Inject tenant-level access control into env (scoped to this request)
    import os
    prev_ch = os.environ.get("ALLOWED_CHANNEL_IDS")
    prev_usr = os.environ.get("ALLOWED_USER_IDS")

    if tenant.allowed_channels:
        os.environ["ALLOWED_CHANNEL_IDS"] = tenant.allowed_channels
    if tenant.allowed_users:
        os.environ["ALLOWED_USER_IDS"] = tenant.allowed_users

    try:
        next()
    finally:
        # Reset ContextVar and env
        KOLAY_TOKEN_CTX.reset(token)
        if prev_ch is not None:
            os.environ["ALLOWED_CHANNEL_IDS"] = prev_ch
        elif "ALLOWED_CHANNEL_IDS" in os.environ and tenant.allowed_channels:
            del os.environ["ALLOWED_CHANNEL_IDS"]
        if prev_usr is not None:
            os.environ["ALLOWED_USER_IDS"] = prev_usr
        elif "ALLOWED_USER_IDS" in os.environ and tenant.allowed_users:
            del os.environ["ALLOWED_USER_IDS"]
