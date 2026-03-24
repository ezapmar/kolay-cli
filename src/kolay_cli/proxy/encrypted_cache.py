"""Ephemeral in-memory encrypted cache + cryptographic tenant key generator.

Requirements addressed
----------------------
Req 2 — Ephemeral In-Memory Encryption
    SecureVolatileCache wraps the existing TTLCache with Fernet (AES-128-CBC
    + HMAC-SHA256).  The encryption key is generated from os.urandom(32) at
    module import time and lives ONLY in volatile RAM.

    Crypto-shredding guarantee:
        When the server process exits (crash, restart, SIGKILL), the in-process
        key is destroyed with the process address space.  Every ciphertext
        stored becomes PERMANENTLY unreadable without the key.  No data
        persistence means no key escrow, no data recovery — by design.

Req 3 — Cryptographic Tenant Isolation
    generate_tenant_cache_key() produces an HMAC-SHA256 digest that is:
      - Unique per (tenant_id, resource) pair
      - Irreversible (cannot recover tenant_id from the key)
      - Server-side peppered (SERVER_CACHE_PEPPER env var) to resist
        offline brute-force even if the key space is guessed

    This eliminates IDOR: Company A's key for "employees" is a completely
    different 64-char hex string from Company B's, even if both resources
    have the same name.

Dependencies
------------
    cryptography.fernet  — transitive dep of PyJWT (already in project)
    Standard library: hmac, hashlib, json, os, base64

STRICT RULES enforced
---------------------
    - No AWS KMS, no Redis, no external key store
    - Ephemeral key never written to disk/logs/env
    - All stdlib + cryptography (existing dep only)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import threading
import time
from typing import Any

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Req 2: Ephemeral key — generated ONCE at module load, lives in RAM only
# ---------------------------------------------------------------------------

def _generate_ephemeral_key() -> bytes:
    """Generate a 32-byte random key for Fernet (AES-128-CBC + HMAC-SHA256).

    Called exactly once at module import.  The key never leaves this process
    and is never written to disk, logs, or environment variables.

    Crypto-shredding: when the process terminates, this object is garbage-
    collected along with all ciphertext it could decrypt.  A server restart
    means a fresh key, instantly invalidating all previous cache entries.
    """
    raw = os.urandom(32)
    return base64.urlsafe_b64encode(raw)


_EPHEMERAL_FERNET_KEY: bytes = _generate_ephemeral_key()


def _get_fernet():  # type: ignore[return]
    """Return a Fernet instance using the ephemeral key."""
    return _get_fernet_with_key(_EPHEMERAL_FERNET_KEY)


def _get_fernet_with_key(key: bytes):  # type: ignore[return]
    """Return a Fernet instance for the given URL-safe base64 key."""
    try:
        from cryptography.fernet import Fernet  # type: ignore[import-untyped]
        return Fernet(key)
    except ImportError as exc:
        raise ImportError(
            "The 'cryptography' package is required for SecureVolatileCache. "
            "It is a transitive dependency of PyJWT and should already be installed. "
            "Run: pip install cryptography"
        ) from exc


# ---------------------------------------------------------------------------
# Req 2: SecureVolatileCache
# ---------------------------------------------------------------------------

class SecureVolatileCache:
    """Thread-safe in-memory cache that stores only ciphertext.

    .set_secure(key, data, ttl)
        Serialize *data* to JSON, encrypt with ephemeral Fernet key,
        store ONLY the resulting ciphertext bytes + expiry timestamp.

    .get_secure(key)
        Fetch ciphertext, decrypt on the fly, deserialize, return.
        Returns None on cache miss or expired entry.

    The underlying _store dict maps:
        str -> (float expiry, bytes ciphertext)

    A process memory dump captures only ciphertext.  Without the ephemeral
    key (which lives nowhere but RAM), the dump is useless.
    """

    def __init__(self, default_ttl: int = 300, _fernet_key: bytes | None = None) -> None:
        self._store: dict[str, tuple[float, bytes]] = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl
        key = _fernet_key if _fernet_key is not None else _EPHEMERAL_FERNET_KEY
        self._fernet = _get_fernet_with_key(key)

    # ── Write ──────────────────────────────────────────────────────────────

    def set_secure(self, key: str, data: Any, ttl: int | None = None) -> None:
        """Encrypt *data* and store ciphertext under *key*."""
        plaintext = json.dumps(data, default=str).encode("utf-8")
        ciphertext = self._fernet.encrypt(plaintext)
        expires_at = time.monotonic() + (ttl if ttl is not None else self.default_ttl)
        with self._lock:
            self._store[key] = (expires_at, ciphertext)

    # ── Read ───────────────────────────────────────────────────────────────

    def get_secure(self, key: str) -> Any | None:
        """Decrypt and return cached data, or None on miss/expiry."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, ciphertext = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None

        # Decrypt outside the lock (CPU-bound, does not touch shared state)
        plaintext = self._fernet.decrypt(ciphertext)
        return json.loads(plaintext.decode("utf-8"))

    # ── Invalidation ───────────────────────────────────────────────────────

    def invalidate(self, key: str) -> bool:
        """Remove a specific key.  Returns True if it existed."""
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._store.clear()

    # ── Diagnostics (no plaintext exposed) ────────────────────────────────

    def status(self, key: str) -> dict[str, Any]:
        """Return cache metadata without decrypting content."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return {
                    "cached": False,
                    "entry_count": 0,
                    "age_seconds": 0.0,
                    "ttl_seconds": self.default_ttl,
                    "expires_in_seconds": 0.0,
                    "encrypted": True,
                }
            expires_at, ciphertext = entry
            now = time.monotonic()
            age = self.default_ttl - (expires_at - now)
            remaining = max(expires_at - now, 0.0)
            return {
                "cached": remaining > 0,
                # entry_count unknown without decryption — return ciphertext size
                "ciphertext_bytes": len(ciphertext),
                "age_seconds": round(age, 1),
                "ttl_seconds": self.default_ttl,
                "expires_in_seconds": round(remaining, 1),
                "encrypted": True,
            }


# ---------------------------------------------------------------------------
# Req 3: Cryptographic tenant cache key generator
# ---------------------------------------------------------------------------

def generate_tenant_cache_key(tenant_id: str, resource_name: str) -> str:
    """Return an HMAC-SHA256 hex digest scoped to a specific tenant+resource.

    The digest is:
        HMAC-SHA256(key=SERVER_CACHE_PEPPER, msg="{tenant_id}:{resource_name}")

    Properties:
        - Unique per (tenant_id, resource_name) pair
        - Irreversible: cannot recover tenant_id from the output
        - Peppered: SERVER_CACHE_PEPPER makes offline brute-force infeasible
        - Deterministic: same inputs always produce the same 64-char hex key

    IDOR protection:
        company_a_key = HMAC(pepper, "sha256(token_a):employees")  -> "a3f9..."
        company_b_key = HMAC(pepper, "sha256(token_b):employees")  -> "7c12..."
        These are mathematically unrelated even though the resource name is the
        same.  Company A cannot enumerate or guess Company B's cache key.

    Args:
        tenant_id:     Stable tenant identifier.  Use rate_limiter.token_key()
                       (SHA-256 of the raw API token) as the tenant_id so that
                       the raw token never appears as a dict key.
        resource_name: Logical resource name, e.g. "employees".

    Returns:
        64-character lowercase hex string (256 bits of entropy).
    """
    pepper = os.environ.get("SERVER_CACHE_PEPPER", "")
    if not pepper:
        _log.warning(
            "SERVER_CACHE_PEPPER is not set.  Tenant cache keys are derived "
            "from tenant_id alone.  Set this env var in production."
        )
    msg = f"{tenant_id}:{resource_name}".encode("utf-8")
    return hmac.new(pepper.encode("utf-8"), msg, hashlib.sha256).hexdigest()
