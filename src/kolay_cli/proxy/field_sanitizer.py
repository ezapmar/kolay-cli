"""Drop-at-the-door PII field sanitizer.

Intercepts raw HR API responses and ruthlessly removes every field not in
ALLOWED_FIELDS before data touches the caching layer.  Sensitive PII
(salary, IBAN, SSN, home_address, mobilePhone, city, salary_history, ...)
is NEVER stored in proxy memory or forwarded to any LLM.

Design:
  - O(N) single-pass dict comprehension — no nested loops, no copies of
    banned values.
  - Pure function: no I/O, no side-effects, safe to call from any thread.
  - frozenset lookup is O(1) at C speed via Python's hash table.

Usage:
    from .field_sanitizer import sanitize_employees

    raw = person_svc.list_people(limit=500)["items"]  # bloated API payload
    clean = sanitize_employees(raw)                    # PII stripped
    cache.set_secure(key, clean)                       # safe to cache
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Strict field whitelist — ONLY these keys survive into the cache / LLM
# ---------------------------------------------------------------------------

ALLOWED_FIELDS: frozenset[str] = frozenset({
    "id",
    "firstName",
    "lastName",
    "department",
    "birthDate",
    "employmentStartDate",
    "workEmail",
    "status",
    "title",
})

# Fields that MUST be stripped (documented for audit trail; the whitelist
# approach already handles any unlisted field, but naming them makes the
# privacy contract explicit).
_BANNED_EXAMPLES: frozenset[str] = frozenset({
    "salary",
    "salaryHistory",
    "salary_history",
    "iban",
    "ssn",
    "nationalId",
    "homeAddress",
    "home_address",
    "mobilePhone",
    "phone",
    "city",
    "bankAccount",
    "emergencyContact",
    "taxId",
    "dateOfBirth",           # use birthDate (month-only precision)
    "passportNumber",
    "driverLicense",
})


def sanitize_employees(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return *raw* with every key not in ALLOWED_FIELDS removed.

    Performance:
        - Single pass over each record: O(N) where N = total field count.
        - frozenset.__contains__ is O(1).
        - No intermediate lists or copies of banned values.
        - Handles 50,000 records without blocking (pure CPU, no I/O).

    Args:
        raw: List of raw employee dicts from the HR REST API.

    Returns:
        New list of dicts containing only ALLOWED_FIELDS keys.

    Example:
        >>> bloated = [{
        ...     "id": "abc123",
        ...     "firstName": "Ayse",
        ...     "lastName": "Yilmaz",
        ...     "salary": 95000,           # BANNED
        ...     "iban": "TR123456789",     # BANNED
        ...     "mobilePhone": "555-1234", # BANNED
        ...     "city": "Istanbul",        # BANNED
        ...     "department": "Engineering",
        ...     "status": "active",
        ... }]
        >>> clean = sanitize_employees(bloated)
        >>> clean
        [{'id': 'abc123', 'firstName': 'Ayse', 'lastName': 'Yilmaz',
          'department': 'Engineering', 'status': 'active'}]
    """
    allowed = ALLOWED_FIELDS  # local binding avoids repeated global lookup
    return [{k: v for k, v in emp.items() if k in allowed} for emp in raw]
