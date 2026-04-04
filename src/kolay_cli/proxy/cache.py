"""In-memory TTL cache for employee API responses.

Security rationalization (platform.md §3.1):
  L6:  Standard profile uses plaintext TTLCache. Encrypting RAM is security
       theater — if an attacker reads process memory, they also read the
       in-process decryption key.  Enterprise profile retains AES-256-GCM
       for compliance checkbox requirements.
  L13: Cache keys are plain "{tenant_id}:{resource}" strings. HMAC hashing
       added no real isolation since tenants are already separated by token
       at the auth layer.
  L4:  Field sanitizer now uses a denylist (system metadata only), preserving
       all HR fields visible in the Kolay IK web UI.

Configuration (env vars):
  MCP_CACHE_TTL_SECONDS  - cache lifetime in seconds (default: 300)
  MCP_MOCK_DATA          - "true" to use synthetic 3000-employee data
  KOLAY_SECURITY_PROFILE - "enterprise" to enable AES-256-GCM cache encryption
"""
from __future__ import annotations

import os
import random
import string
import time
import threading
from datetime import date
from typing import Any

from .field_sanitizer import sanitize_employees


# ---------------------------------------------------------------------------
# Thread-safe plaintext TTL Cache (Standard profile default)
# ---------------------------------------------------------------------------

class TTLCache:
    """Thread-safe in-memory key/value store with per-entry TTL."""

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
# Module-level cache instance
# ---------------------------------------------------------------------------

_cache_ttl = int(os.environ.get("MCP_CACHE_TTL_SECONDS", "300"))
_profile = os.environ.get("KOLAY_SECURITY_PROFILE", "standard").lower()
_is_enterprise = (_profile == "enterprise")

if _is_enterprise:
    from .encrypted_cache import SecureVolatileCache
    employee_cache = SecureVolatileCache(default_ttl=_cache_ttl)
else:
    employee_cache = TTLCache(default_ttl=_cache_ttl)

_RESOURCE_NAME = "employees"


def _cache_key(tenant_id: str, resource: str = _RESOURCE_NAME) -> str:
    """Simple tenant-prefixed cache key (L13 rationalized)."""
    return f"{tenant_id}:{resource}"


def _get_cache_key() -> str:
    """Derive a per-tenant cache key from the current request context."""
    from .auth import KOLAY_TOKEN_CTX
    from .rate_limiter import token_key

    raw_token = KOLAY_TOKEN_CTX.get()
    if raw_token:
        tenant_id = token_key(raw_token)
    else:
        tenant_id = "single_tenant"

    return _cache_key(tenant_id)


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
    """Generate synthetic employee records."""
    rng = random.Random(42)
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
            "id": emp_id,
            "firstName": first,
            "lastName": last,
            "workEmail": f"{first.lower()}.{last.lower()}.{i}@example.com",
            "department": dept,
            "birthDate": birth_date.isoformat(),
            "employmentStartDate": start_date.isoformat(),
            "status": "active",
            "title": rng.choice(["Engineer", "Manager", "Analyst", "Specialist", "Lead", "Director", "Intern"]),
            "salary": round(rng.uniform(8000, 120000), 2),
            "mobilePhone": f"+90 5{rng.randint(30, 59)} {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
            "city": rng.choice(["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya"]),
        })
    return employees


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_all_employees() -> list[dict[str, Any]]:
    """Return sanitized employees for the current tenant, hitting cache first."""
    cache_key = _get_cache_key()

    if _is_enterprise:
        cached = employee_cache.get_secure(cache_key)
    else:
        cached = employee_cache.get(cache_key)

    if cached is not None:
        return cached

    use_mock = os.environ.get("MCP_MOCK_DATA", "").lower() in ("1", "true", "yes")
    if use_mock:
        raw_data: list[dict[str, Any]] = _generate_mock_employees(3000)
    else:
        from ..services import person as person_svc
        result = person_svc.list_people(limit=500, status="active")
        raw_data = result.get("items", [])

    # L4: Strip system-internal metadata (denylist). HR fields pass through.
    clean_data = sanitize_employees(raw_data)

    if _is_enterprise:
        employee_cache.set_secure(cache_key, clean_data)
    else:
        employee_cache.set(cache_key, clean_data)

    return clean_data


def cache_status() -> dict[str, Any]:
    """Return diagnostic info about the employee cache."""
    cache_key = _get_cache_key()
    return employee_cache.status(cache_key)


def invalidate_cache() -> dict[str, str]:
    """Force-clear the employee cache for the current tenant."""
    cache_key = _get_cache_key()
    employee_cache.invalidate(cache_key)
    return {"status": "invalidated", "message": "Employee cache cleared. Next request will re-fetch."}


def invalidate_tenant(tenant_id: str) -> bool:
    """Purge cached data for a specific tenant ID."""
    cache_key = _cache_key(tenant_id)
    return employee_cache.invalidate(cache_key)




