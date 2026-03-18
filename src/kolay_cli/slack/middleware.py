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


def tenant_middleware(payload: dict, body: dict, next: Any, client: Any = None, ack: Any = None) -> None:
    """Slack Bolt global middleware.

    Runs before every slash-command / action / view-submission handler.
    1. Extracts ``team_id`` from the Slack payload.
    2. Looks up the tenant in the store.
    3. If found → injects tenant's Kolay token into ``KOLAY_TOKEN_CTX``.
    4. If NOT found → falls back to global ``KOLAY_API_TOKEN`` env var
       (single-tenant mode, e.g. Railway with env vars set).
    5. If neither exists → acks and sends an error message.
    """
    import os

    team_id = (
        body.get("team_id")
        or (body.get("team") or {}).get("id")
        or ""
    )

    store = _get_store()
    tenant = store.find(team_id) if team_id else None
    print(f"[middleware] team_id={team_id} tenant={'FOUND' if tenant else 'NONE'}", flush=True)

    if tenant is not None:
        print(f"[middleware] setting KOLAY_TOKEN_CTX, token_len={len(tenant.kolay_api_token)}", flush=True)
        # ── Multi-tenant path: use tenant's stored token ──────────────
        token = KOLAY_TOKEN_CTX.set(tenant.kolay_api_token)

        # Inject tenant-level access control into env (scoped to this request)
        prev_ch = os.environ.get("ALLOWED_CHANNEL_IDS")
        prev_usr = os.environ.get("ALLOWED_USER_IDS")

        if tenant.allowed_channels:
            os.environ["ALLOWED_CHANNEL_IDS"] = tenant.allowed_channels
        if tenant.allowed_users:
            os.environ["ALLOWED_USER_IDS"] = tenant.allowed_users

        try:
            next()
        finally:
            KOLAY_TOKEN_CTX.reset(token)
            if prev_ch is not None:
                os.environ["ALLOWED_CHANNEL_IDS"] = prev_ch
            elif "ALLOWED_CHANNEL_IDS" in os.environ and tenant.allowed_channels:
                del os.environ["ALLOWED_CHANNEL_IDS"]
            if prev_usr is not None:
                os.environ["ALLOWED_USER_IDS"] = prev_usr
            elif "ALLOWED_USER_IDS" in os.environ and tenant.allowed_users:
                del os.environ["ALLOWED_USER_IDS"]
        return

    # ── Single-tenant fallback: use global KOLAY_API_TOKEN env var ─────
    global_token = os.environ.get("KOLAY_API_TOKEN", "").strip()
    if global_token:
        token = KOLAY_TOKEN_CTX.set(global_token)
        try:
            next()
        finally:
            KOLAY_TOKEN_CTX.reset(token)
        return

    # ── No token at all: ack and inform the user ──────────────────────
    # We must call next() so Bolt can ack the request and avoid Slack's
    # 3-second timeout. Instead we'll pass through and the dispatcher
    # will hit @require_auth which returns a proper error.
    next()

