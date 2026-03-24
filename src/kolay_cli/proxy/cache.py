"""In-memory TTL cache for expensive API responses.

Security layers applied (in order):
  1. Drop-at-the-door field sanitization   (field_sanitizer.sanitize_employees)
     PII is stripped from raw API payloads BEFORE data reaches the cache.
  2. Encrypted volatile cache              (secure_cache.SecureVolatileCache)
     Only Fernet ciphertext lives in RAM. Plaintext is never stored.
  3. Per-tenant HMAC cache keys            (secure_cache.generate_tenant_cache_key)
     Each tenant's cache entry has a unique, irreversible key.
     IDOR between tenants is mathematically impossible.

Configuration (env vars):
  MCP_CACHE_TTL_SECONDS  – cache lifetime in seconds (default: 300)
  MCP_MOCK_DATA          – "true" to use synthetic 3000-employee data
  SERVER_CACHE_PEPPER    – HMAC pepper for tenant key derivation (required in prod)

Usage:
  from .ttl_cache import fetch_all_employees, cache_status, invalidate_cache
"""
from __future__ import annotations

import os
import random
import string
import time
from datetime import date
from typing import Any

from .field_sanitizer import sanitize_employees
from .encrypted_cache import SecureVolatileCache, generate_tenant_cache_key


# ---------------------------------------------------------------------------
# Generic plaintext TTL Cache (kept for non-sensitive data if needed)
# ---------------------------------------------------------------------------

import threading


class TTLCache:
    """Thread-safe in-memory key/value store with per-entry TTL (plaintext)."""

    def __init__(self, default_ttl: int = 300) -> None:
        self._store: dict[str, tuple[float, Any]] = {}  # key -> (expires_at, value)
        self._lock = threading.Lock()
        self.default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Return cached value if present and not expired, else None."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value with optional custom TTL."""
        with self._lock:
            expires_at = time.monotonic() + (ttl if ttl is not None else self.default_ttl)
            self._store[key] = (expires_at, value)

    def invalidate(self, key: str) -> bool:
        """Remove a specific key. Returns True if it existed."""
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._store.clear()

    def status(self, key: str) -> dict[str, Any]:
        """Return diagnostic info about a cache entry."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return {
                    "cached": False,
                    "entry_count": 0,
                    "age_seconds": 0.0,
                    "ttl_seconds": self.default_ttl,
                    "expires_in_seconds": 0.0,
                }
            expires_at, value = entry
            now = time.monotonic()
            age = self.default_ttl - (expires_at - now)
            remaining = max(expires_at - now, 0.0)
            count = len(value) if isinstance(value, list) else 1
            return {
                "cached": remaining > 0,
                "entry_count": count,
                "age_seconds": round(age, 1),
                "ttl_seconds": self.default_ttl,
                "expires_in_seconds": round(remaining, 1),
            }


# ---------------------------------------------------------------------------
# Module-level ENCRYPTED employee cache instance
# ---------------------------------------------------------------------------

_cache_ttl = int(os.environ.get("MCP_CACHE_TTL_SECONDS", "300"))

# SecureVolatileCache: stores only Fernet ciphertext — plaintext never at rest
employee_cache = SecureVolatileCache(default_ttl=_cache_ttl)

_RESOURCE_NAME = "employees"


def _get_cache_key() -> str:
    """Derive a per-tenant HMAC cache key from the current request context.

    The tenant_id is the SHA-256 hash of the raw API token (rate_limiter.token_key
    already computes this).  The raw token is never used as a dict key.

    Falls back to a constant key in single-tenant / non-HTTP mode.
    """
    from .auth import KOLAY_TOKEN_CTX
    from .rate_limiter import token_key

    raw_token = KOLAY_TOKEN_CTX.get()
    if raw_token:
        tenant_id = token_key(raw_token)
    else:
        # Single-tenant mode (stdio, local dev): use a fixed but still peppered key
        tenant_id = "single_tenant"

    return generate_tenant_cache_key(tenant_id, _RESOURCE_NAME)


# ---------------------------------------------------------------------------
# Mock data generator (3000 synthetic employees)
# ---------------------------------------------------------------------------

_DEPARTMENTS = [
    "Engineering", "Product", "Design", "Marketing", "Sales",
    "Finance", "HR", "Legal", "Operations", "Customer Success",
    "Data Science", "DevOps", "QA", "Security", "Support",
]

_FIRST_NAMES = [
    "Ali", "Ayse", "Mehmet", "Fatma", "Mustafa", "Zeynep", "Ahmet",
    "Elif", "Hasan", "Merve", "Emre", "Selin", "Burak", "Deniz",
    "Can", "Ece", "Omer", "Buse", "Kerem", "Gizem",
]

_LAST_NAMES = [
    "Yilmaz", "Kaya", "Demir", "Celik", "Sahin", "Ozturk", "Aydin",
    "Arslan", "Dogan", "Kilic", "Aksoy", "Korkmaz", "Erdogan",
    "Ucar", "Gunes", "Polat", "Koc", "Karaca", "Acar", "Tas",
]


def _generate_mock_employees(count: int = 3000) -> list[dict[str, Any]]:
    """Generate synthetic employee records that already include banned fields.

    This mirrors a realistic HR API response.  sanitize_employees() is applied
    downstream, so fields like 'salary' and 'mobilePhone' never survive to RAM.
    """
    rng = random.Random(42)  # Deterministic seed for reproducibility
    employees: list[dict[str, Any]] = []
    for i in range(count):
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)
        dept = rng.choice(_DEPARTMENTS)
        birth_date = date(
            rng.randint(1965, 2002),
            rng.randint(1, 12),
            rng.randint(1, 28),
        )
        start_date = date(
            rng.randint(2015, 2025),
            rng.randint(1, 12),
            rng.randint(1, 28),
        )
        emp_id = "".join(rng.choices(string.hexdigits[:16], k=32))

        employees.append({
            # -- Allowed fields --
            "id": emp_id,
            "firstName": first,
            "lastName": last,
            "workEmail": f"{first.lower()}.{last.lower()}.{i}@example.com",
            "department": dept,
            "birthDate": birth_date.isoformat(),
            "employmentStartDate": start_date.isoformat(),
            "status": "active",
            "title": rng.choice(["Engineer", "Manager", "Analyst", "Specialist", "Lead", "Director", "Intern"]),
            # -- Banned fields (dropped by sanitize_employees before caching) --
            "salary": round(rng.uniform(8000, 120000), 2),
            "mobilePhone": f"+90 5{rng.randint(30, 59)} {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
            "city": rng.choice(["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya"]),
        })
    return employees


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_all_employees() -> list[dict[str, Any]]:
    """Return sanitized employees for the current tenant, hitting cache first.

    Security pipeline:
        raw API / mock  ->  sanitize_employees()  ->  encrypt  ->  SecureVolatileCache
        SecureVolatileCache  ->  decrypt  ->  sanitized list[dict]  ->  caller

    If MCP_MOCK_DATA is set, returns 3000 synthetic records.
    Otherwise calls the real person_list API with a high limit.
    """
    cache_key = _get_cache_key()
    cached = employee_cache.get_secure(cache_key)
    if cached is not None:
        return cached

    use_mock = os.environ.get("MCP_MOCK_DATA", "").lower() in ("1", "true", "yes")
    if use_mock:
        raw_data: list[dict[str, Any]] = _generate_mock_employees(3000)
    else:
        from .services import person as person_svc
        result = person_svc.list_people(limit=500, status="active")
        raw_data = result.get("items", [])

    # --- Req 1: Drop-at-the-door ---
    # PII fields are stripped HERE, before any caching or further processing.
    clean_data = sanitize_employees(raw_data)

    # --- Req 2: Encrypted cache write ---
    # Only ciphertext is stored in RAM.
    employee_cache.set_secure(cache_key, clean_data)

    return clean_data


def cache_status() -> dict[str, Any]:
    """Return diagnostic info about the employee cache (no plaintext exposed)."""
    cache_key = _get_cache_key()
    return employee_cache.status(cache_key)


def invalidate_cache() -> dict[str, str]:
    """Force-clear the employee cache for the current tenant."""
    cache_key = _get_cache_key()
    employee_cache.invalidate(cache_key)
    return {"status": "invalidated", "message": "Employee cache cleared. Next request will re-fetch."}



