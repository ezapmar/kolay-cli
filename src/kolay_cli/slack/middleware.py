"""Slack Bolt middleware: inject per-tenant Kolay token into the environment."""
from __future__ import annotations

import os
import threading
from typing import Any

from .tenant_store import TenantStore


# Module-level store — initialised lazily on first use.
_store: TenantStore | None = None
_env_lock = threading.Lock()


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
    Since Bolt dispatches handlers to a ThreadPoolExecutor, ContextVars
    set here (MainThread) are NOT visible in the handler thread.

    Instead, we inject the tenant's Kolay API token into:
      1. os.environ["KOLAY_API_TOKEN"] — visible to all threads
      2. Bolt's context dict — available as `context["kolay_token"]`
    """
    team_id = (
        body.get("team_id")
        or (body.get("team") or {}).get("id")
        or ""
    )

    store = _get_store()
    tenant = store.find(team_id) if team_id else None
    print(f"[middleware] team_id={team_id} tenant={'FOUND' if tenant else 'NONE'}", flush=True)

    kolay_token: str | None = None

    if tenant is not None:
        kolay_token = tenant.kolay_api_token
        print(f"[middleware] kolay_token from tenant, len={len(kolay_token)}", flush=True)
    else:
        # Single-tenant fallback
        kolay_token = os.environ.get("KOLAY_API_TOKEN", "").strip() or None
        if kolay_token:
            print("[middleware] kolay_token from env var fallback", flush=True)

    if kolay_token:
        # Inject into env so KolayClient (any thread) can see it
        with _env_lock:
            prev_token = os.environ.get("KOLAY_API_TOKEN")
            os.environ["KOLAY_API_TOKEN"] = kolay_token

            # Also inject tenant-level access control
            prev_ch = os.environ.get("ALLOWED_CHANNEL_IDS")
            prev_usr = os.environ.get("ALLOWED_USER_IDS")
            if tenant and tenant.allowed_channels:
                os.environ["ALLOWED_CHANNEL_IDS"] = tenant.allowed_channels
            if tenant and tenant.allowed_users:
                os.environ["ALLOWED_USER_IDS"] = tenant.allowed_users

        try:
            next()
        finally:
            # Restore previous env state
            with _env_lock:
                if prev_token is not None:
                    os.environ["KOLAY_API_TOKEN"] = prev_token
                elif "KOLAY_API_TOKEN" in os.environ:
                    del os.environ["KOLAY_API_TOKEN"]

                if prev_ch is not None:
                    os.environ["ALLOWED_CHANNEL_IDS"] = prev_ch
                elif "ALLOWED_CHANNEL_IDS" in os.environ and tenant and tenant.allowed_channels:
                    del os.environ["ALLOWED_CHANNEL_IDS"]

                if prev_usr is not None:
                    os.environ["ALLOWED_USER_IDS"] = prev_usr
                elif "ALLOWED_USER_IDS" in os.environ and tenant and tenant.allowed_users:
                    del os.environ["ALLOWED_USER_IDS"]
        return

    # No token at all — pass through, dispatcher will return auth error
    print("[middleware] no token available, passing through", flush=True)
    next()
