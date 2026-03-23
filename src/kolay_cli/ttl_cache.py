"""In-memory TTL cache for expensive API responses.

Prevents rapid-fire LLM reasoning steps from spamming the external
Kolay IK REST API.  Uses only stdlib (time, threading, typing).

Configuration (env vars):
  MCP_CACHE_TTL_SECONDS  – cache lifetime in seconds (default: 300)
  MCP_MOCK_DATA          – "true" to use synthetic 3000-employee data

Usage:
  from .ttl_cache import fetch_all_employees, cache_status, invalidate_cache
"""
from __future__ import annotations

import os
import random
import string
import threading
import time
from datetime import date, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Generic TTL Cache
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
# Module-level employee cache instance
# ---------------------------------------------------------------------------

_cache_ttl = int(os.environ.get("MCP_CACHE_TTL_SECONDS", "300"))
employee_cache = TTLCache(default_ttl=_cache_ttl)

_CACHE_KEY = "all_employees"


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
    """Generate synthetic employee records for testing/demo."""
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
            "id": emp_id,
            "firstName": first,
            "lastName": last,
            "workEmail": f"{first.lower()}.{last.lower()}.{i}@example.com",
            "department": dept,
            "birthDate": birth_date.isoformat(),
            "employmentStartDate": start_date.isoformat(),
            "status": "active",
            "mobilePhone": f"+90 5{rng.randint(30, 59)} {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
            "title": rng.choice(["Engineer", "Manager", "Analyst", "Specialist", "Lead", "Director", "Intern"]),
            "salary": round(rng.uniform(8000, 120000), 2),
            "city": rng.choice(["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya"]),
        })
    return employees


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_all_employees() -> list[dict[str, Any]]:
    """Return all employees, hitting cache first.

    If MCP_MOCK_DATA is set, returns 3000 synthetic records
    (simulating a large Kolay IK tenant).  Otherwise calls the
    real person_list API with a high limit.
    """
    cached = employee_cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    use_mock = os.environ.get("MCP_MOCK_DATA", "").lower() in ("1", "true", "yes")
    if use_mock:
        data = _generate_mock_employees(3000)
    else:
        from .services import person as person_svc
        # Fetch with a high limit to maximise cache value.
        # The API itself may paginate; we fetch the first large page.
        result = person_svc.list_people(limit=500, status="active")
        data = result.get("items", [])

    employee_cache.set(_CACHE_KEY, data)
    return data


def cache_status() -> dict[str, Any]:
    """Return diagnostic info about the employee cache."""
    return employee_cache.status(_CACHE_KEY)


def invalidate_cache() -> dict[str, str]:
    """Force-clear the employee cache."""
    employee_cache.invalidate(_CACHE_KEY)
    return {"status": "invalidated", "message": "Employee cache cleared. Next request will re-fetch."}
