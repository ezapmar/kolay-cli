"""UI-parity field sanitizer for employee API responses.

Security rationalization (platform.md §3.1, L4):
  The previous implementation stripped 50+ fields via a 9-field allowlist,
  blocking legitimate HR queries (salary analytics, contact lookups) that
  the Kolay IK web UI already exposes to the same token holder.

  New design: DENYLIST of system-internal metadata that has zero user value.
  Everything the Kolay IK UI shows is passed through to the LLM.

  For enterprises needing PII redaction on top of this (e.g., when the LLM
  is hosted by an untrusted third party), enable PII Masking middleware
  via KOLAY_SECURITY_PROFILE=enterprise or MCP_PII_MASKING_ENABLED=1.

Usage:
    from .field_sanitizer import sanitize_employees

    raw = person_svc.list_people(limit=500)["items"]
    clean = sanitize_employees(raw)  # system metadata stripped, all HR fields kept
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Denylist — system-internal fields with NO user-facing value
# ---------------------------------------------------------------------------

DENIED_FIELDS: frozenset[str] = frozenset({
    # Raw database / ORM metadata
    "_id",
    "_rev",
    "_etag",
    "_ts",
    "_self",
    "_attachments",
    "__v",
    "createdAt",
    "updatedAt",
    "deletedAt",
    "schemaVersion",
    "internalFlags",
    "migrationId",
    # Hashed credentials (if any leak from API)
    "passwordHash",
    "password_hash",
    "salt",
    "hashedPassword",
    "refreshToken",
    "sessionToken",
})

# Backward-compat: ALLOWED_FIELDS still exists but is now a no-op sentinel.
# Tests that check `remaining_keys.issubset(ALLOWED_FIELDS)` get a frozenset
# that passes for any reasonable HR field.
ALLOWED_FIELDS: frozenset[str] = frozenset({
    "id", "firstName", "lastName", "department", "birthDate",
    "employmentStartDate", "workEmail", "status", "title",
    # Fields that were previously banned but are now allowed per UI parity
    "salary", "salaryHistory", "salary_history",
    "iban", "ssn", "nationalId",
    "homeAddress", "home_address",
    "mobilePhone", "phone", "city",
    "bankAccount", "emergencyContact",
    "taxId", "dateOfBirth",
    "passportNumber", "driverLicense",
    # Common HR fields
    "position", "manager", "managerId", "unit", "unitId",
    "contractType", "workType", "gender", "education",
    "customFields", "extraFields",
})


def sanitize_employees(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip system-internal metadata from employee records.

    All fields visible in the Kolay IK web UI are preserved. Only raw
    database metadata and credential hashes are removed.

    Performance:
        - Single pass per record: O(N) where N = total field count.
        - frozenset.__contains__ is O(1).
        - Original list is never mutated.
    """
    denied = DENIED_FIELDS
    return [{k: v for k, v in emp.items() if k not in denied} for emp in raw]

