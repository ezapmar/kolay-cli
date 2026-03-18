"""Slack Bolt middleware: inject per-tenant Kolay token into the environment."""
from __future__ import annotations

import os
from typing import Any

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


def tenant_middleware(payload: dict, body: dict, next: Any, context: dict | None = None, **kwargs: Any) -> None:
    """Slack Bolt global middleware.

    Runs before every slash-command / action / view-submission handler.

    IMPORTANT: Bolt dispatches handlers to a ThreadPoolExecutor, so:
      - ContextVars set here (MainThread) are NOT visible in the handler thread.
      - os.environ set HERE and cleaned in `finally` gets cleaned BEFORE
        the handler thread reads it (next() is non-blocking).

    Solution: Set os.environ["KOLAY_API_TOKEN"] and do NOT clean it up.
    The value persists for the handler thread to read. Each incoming request
    overwrites it with the correct tenant's token before dispatching.
    """
    team_id = (
        body.get("team_id")
        or (body.get("team") or {}).get("id")
        or ""
    )

    store = _get_store()
    tenant = store.find(team_id) if team_id else None

    kolay_token: str | None = None

    if tenant is not None:
        kolay_token = tenant.kolay_api_token
        # Also inject tenant-level access control
        if tenant.allowed_channels:
            os.environ["ALLOWED_CHANNEL_IDS"] = tenant.allowed_channels
        if tenant.allowed_users:
            os.environ["ALLOWED_USER_IDS"] = tenant.allowed_users
    else:
        # Single-tenant fallback
        kolay_token = os.environ.get("KOLAY_API_TOKEN", "").strip() or None

    if kolay_token:
        # Set env var — visible to ALL threads including the handler's ThreadPool worker.
        # We do NOT clean this up because next() is non-blocking and the handler
        # thread needs the value to persist until it reads it.
        os.environ["KOLAY_API_TOKEN"] = kolay_token

    next()
