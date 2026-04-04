"""Proxy security & privacy layer — zero FastMCP dependencies.

All modules in this package are pure stdlib + cryptography.
FastMCP can be upgraded without touching anything here.

Public re-exports (preferred import surface):
    from kolay_cli.proxy import require_auth, resolve_token, KOLAY_TOKEN_CTX
    from kolay_cli.proxy import token_key, check_rate_limit
    from kolay_cli.proxy import circuit_breaker, check_circuit
    from kolay_cli.proxy import scan_and_redact, dlp_scan
    from kolay_cli.proxy import sanitize_employees
    from kolay_cli.proxy import fetch_all_employees, cache_status, invalidate_cache
"""
from __future__ import annotations

# Auth & JWT
from .auth import (
    require_auth,
    requires_permission,
    resolve_token,
    validate_token,
    store_token,
    get_keyring_token,
    delete_token,
    KOLAY_TOKEN_CTX,
    TokenStatus,
)

# Per-token global rate limiter
from .rate_limiter import (
    token_key,
    check_rate_limit,
    cleanup_stale_entries,
    is_rate_limit_enabled,
)

# Per-tool AI circuit breaker
from .circuit_breaker import (
    circuit_breaker,
    check_circuit,
)

# Egress DLP scanner
from .egress_dlp import (
    scan_and_redact,
    dlp_scan,
    scan_string,
)

# Field sanitizer (UI-parity denylist)
from .field_sanitizer import (
    sanitize_employees,
    ALLOWED_FIELDS,
    DENIED_FIELDS,
)

# Employee cache (TTL + encrypted)
from .cache import (
    fetch_all_employees,
    cache_status,
    invalidate_cache,
    TTLCache,
)

__all__ = [
    # auth
    "require_auth", "requires_permission", "resolve_token", "validate_token",
    "store_token", "get_keyring_token", "delete_token",
    "KOLAY_TOKEN_CTX", "TokenStatus",
    # rate limiter
    "token_key", "check_rate_limit", "cleanup_stale_entries", "is_rate_limit_enabled",
    # circuit breaker
    "circuit_breaker", "check_circuit",
    # dlp
    "scan_and_redact", "dlp_scan", "scan_string",
    # field sanitizer
    "sanitize_employees", "ALLOWED_FIELDS", "DENIED_FIELDS",
    # cache
    "fetch_all_employees", "cache_status", "invalidate_cache", "TTLCache",
]
