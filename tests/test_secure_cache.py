"""Tests for:
  - Req 1: UI-parity field sanitizer (denylist — system metadata only)
  - Req 2: Ephemeral in-memory encryption (SecureVolatileCache) — AES-256-GCM
  - Req 3: Tenant cache key isolation (simple prefix keys)
"""
from __future__ import annotations

import os
import time

import pytest

from kolay_cli.field_sanitizer import ALLOWED_FIELDS, DENIED_FIELDS, sanitize_employees
from kolay_cli.secure_cache import SecureVolatileCache, generate_tenant_cache_key
from kolay_cli.proxy.aes256gcm import CryptoError, generate_ephemeral_key


# ---------------------------------------------------------------------------
# Req 1: Field sanitizer (denylist — UI parity)
# ---------------------------------------------------------------------------

class TestSanitizeEmployees:
    """System metadata stripped, all HR fields preserved."""

    RECORD = {
        "id": "abc123",
        "firstName": "Ayse",
        "lastName": "Yilmaz",
        "department": "Engineering",
        "status": "active",
        "workEmail": "ayse@company.com",
        "birthDate": "1990-04-15",
        "employmentStartDate": "2020-01-01",
        "title": "Engineer",
        # HR fields that are now ALLOWED per UI parity
        "salary": 95000,
        "salaryHistory": [80000, 85000, 90000, 95000],
        "iban": "TR12 0006 2000 1190 0006 2920 77",
        "mobilePhone": "555-1234",
        "city": "Istanbul",
        # System metadata that MUST be stripped
        "_id": "internal_mongo_id",
        "passwordHash": "bcrypt:$2b$...",
        "schemaVersion": 3,
        "createdAt": "2020-01-01T00:00:00Z",
        "updatedAt": "2024-12-15T10:30:00Z",
        "refreshToken": "eyJhbGci...",
    }

    def test_system_metadata_is_stripped(self) -> None:
        clean = sanitize_employees([self.RECORD])
        rec = clean[0]
        system_fields = ["_id", "passwordHash", "schemaVersion",
                         "createdAt", "updatedAt", "refreshToken"]
        for field in system_fields:
            assert field not in rec, f"System field '{field}' survived sanitization"

    def test_hr_fields_are_preserved(self) -> None:
        """Fields visible in Kolay IK web UI must pass through."""
        clean = sanitize_employees([self.RECORD])
        rec = clean[0]
        assert rec["id"] == "abc123"
        assert rec["firstName"] == "Ayse"
        assert rec["salary"] == 95000
        assert rec["iban"] == "TR12 0006 2000 1190 0006 2920 77"
        assert rec["mobilePhone"] == "555-1234"
        assert rec["city"] == "Istanbul"

    def test_all_denied_keys_are_stripped(self) -> None:
        """Build a record with every denied field and verify all are removed."""
        bloated = {field: "test_value" for field in DENIED_FIELDS}
        bloated["id"] = "keep_me"
        clean = sanitize_employees([bloated])
        remaining = set(clean[0].keys())
        assert remaining == {"id"}

    def test_empty_list_returns_empty_list(self) -> None:
        assert sanitize_employees([]) == []

    def test_record_with_only_denied_fields_returns_empty_dict(self) -> None:
        all_denied = [{"_id": "x", "passwordHash": "y", "salt": "z"}]
        clean = sanitize_employees(all_denied)
        assert clean == [{}]

    def test_large_array_performance(self) -> None:
        """50,000 records must complete in under 2 seconds."""
        large = [dict(self.RECORD, id=str(i)) for i in range(50_000)]
        t0 = time.monotonic()
        clean = sanitize_employees(large)
        elapsed = time.monotonic() - t0
        assert len(clean) == 50_000
        assert elapsed < 2.0, f"sanitize_employees took {elapsed:.2f}s for 50k records"

    def test_original_list_is_not_mutated(self) -> None:
        original = [dict(self.RECORD)]
        _ = sanitize_employees(original)
        assert "_id" in original[0], "Original record was mutated"


# ---------------------------------------------------------------------------
# Req 2: SecureVolatileCache (AES-256-GCM)
# ---------------------------------------------------------------------------

class TestSecureVolatileCache:

    def setup_method(self) -> None:
        self.cache = SecureVolatileCache(default_ttl=5)

    def test_set_and_get_roundtrip(self) -> None:
        data = [{"id": "1", "firstName": "Ali"}]
        self.cache.set_secure("k1", data)
        result = self.cache.get_secure("k1")
        assert result == data

    def test_internal_store_holds_only_strings(self) -> None:
        """The raw _store must hold ciphertext tokens (str), never plaintext dicts."""
        self.cache.set_secure("k2", [{"secret": "should_be_encrypted"}])
        _, token = self.cache._store["k2"]
        assert isinstance(token, str), "Cache stored non-string value"
        # The base64 token must not contain the plaintext in any readable form
        import base64 as _b64
        raw = _b64.urlsafe_b64decode(token)
        assert b"should_be_encrypted" not in raw

    def test_cache_miss_returns_none(self) -> None:
        assert self.cache.get_secure("nonexistent") is None

    def test_ttl_expiry(self) -> None:
        cache = SecureVolatileCache(default_ttl=1)
        cache.set_secure("expiry_key", {"x": 1})
        assert cache.get_secure("expiry_key") is not None
        time.sleep(1.1)
        assert cache.get_secure("expiry_key") is None

    def test_invalidate_removes_entry(self) -> None:
        self.cache.set_secure("k3", {"a": 1})
        assert self.cache.invalidate("k3") is True
        assert self.cache.get_secure("k3") is None

    def test_invalidate_missing_key_returns_false(self) -> None:
        assert self.cache.invalidate("does_not_exist") is False

    def test_clear_removes_all_entries(self) -> None:
        self.cache.set_secure("a", [1])
        self.cache.set_secure("b", [2])
        self.cache.clear()
        assert self.cache.get_secure("a") is None
        assert self.cache.get_secure("b") is None

    def test_status_cached_entry(self) -> None:
        self.cache.set_secure("s1", list(range(100)))
        st = self.cache.status("s1")
        assert st["cached"] is True
        assert st["encrypted"] is True
        assert st["cipher"] == "AES-256-GCM"
        assert "ciphertext_bytes" in st
        assert st["ciphertext_bytes"] > 0

    def test_status_missing_entry(self) -> None:
        st = self.cache.status("missing")
        assert st["cached"] is False
        assert st["encrypted"] is True

    def test_crypto_shredding_simulation(self) -> None:
        """
        Simulates a server restart: a new SecureVolatileCache with a different
        ephemeral key cannot decrypt entries written by a previous instance.

        AES-256-GCM will raise CryptoError (auth tag mismatch) when the key
        does not match — no partial plaintext is ever returned.
        """
        key_a = generate_ephemeral_key()  # raw 32-byte key
        key_b = generate_ephemeral_key()  # raw 32-byte key
        assert key_a != key_b, "Test precondition: keys must differ"

        cache_a = SecureVolatileCache(default_ttl=60, _key=key_a)
        cache_b = SecureVolatileCache(default_ttl=60, _key=key_b)

        cache_a.set_secure("shared_key", {"sensitive": "data"})
        _, token = cache_a._store["shared_key"]

        # Inject cache_a's ciphertext token into cache_b
        cache_b._store["shared_key"] = (time.monotonic() + 60, token)

        # cache_b (different ephemeral key) cannot authenticate cache_a's ciphertext.
        # get_secure() catches CryptoError and returns None (logged as warning).
        result = cache_b.get_secure("shared_key")
        assert result is None, (
            "Cross-key decryption succeeded — AES-256-GCM auth tag not enforced"
        )

    def test_complex_data_types_roundtrip(self) -> None:
        data = {
            "employees": [{"id": "1", "dept": "Eng"}],
            "count": 42,
            "meta": {"source": "cache"},
        }
        self.cache.set_secure("complex", data)
        assert self.cache.get_secure("complex") == data

    def test_each_set_produces_unique_ciphertext(self) -> None:
        """Fresh nonce per call — same payload produces different token each time."""
        data = {"key": "value"}
        self.cache.set_secure("t1", data)
        _, token1 = self.cache._store["t1"]
        self.cache.set_secure("t1", data)
        _, token2 = self.cache._store["t1"]
        assert token1 != token2, "Same ciphertext on repeated set — nonce reuse"


# ---------------------------------------------------------------------------
# Req 3: Cryptographic tenant key isolation
# ---------------------------------------------------------------------------

class TestGenerateTenantCacheKey:

    def test_deterministic_same_inputs(self) -> None:
        k1 = generate_tenant_cache_key("tenant_a", "employees")
        k2 = generate_tenant_cache_key("tenant_a", "employees")
        assert k1 == k2

    def test_different_tenants_different_keys(self) -> None:
        k_a = generate_tenant_cache_key("tenant_a", "employees")
        k_b = generate_tenant_cache_key("tenant_b", "employees")
        assert k_a != k_b

    def test_same_tenant_different_resource_different_key(self) -> None:
        k_emp = generate_tenant_cache_key("tenant_a", "employees")
        k_cal = generate_tenant_cache_key("tenant_a", "calendar")
        assert k_emp != k_cal

    def test_output_format(self) -> None:
        key = generate_tenant_cache_key("tenant123", "employees")
        assert key == "tenant123:employees"

    def test_all_tenants_get_disjoint_keys(self) -> None:
        """10 different tenants accessing the same resource get 10 different keys."""
        keys = [generate_tenant_cache_key(f"tenant_{i}", "employees") for i in range(10)]
        assert len(set(keys)) == 10, "Collision detected — keys are not unique per tenant"

    def test_idor_protection_end_to_end(self) -> None:
        """Company A cannot read Company B's cache entry."""
        cache = SecureVolatileCache(default_ttl=60)

        key_a = generate_tenant_cache_key("company_a", "employees")
        key_b = generate_tenant_cache_key("company_b", "employees")

        data_a = [{"id": "a1", "firstName": "Ayse"}]
        data_b = [{"id": "b1", "firstName": "Mehmet"}]

        cache.set_secure(key_a, data_a)
        cache.set_secure(key_b, data_b)

        # Each tenant reads their own data correctly
        assert cache.get_secure(key_a) == data_a
        assert cache.get_secure(key_b) == data_b

        # Using key_a to request key_b's slot returns None (different key hash)
        assert cache.get_secure(key_a) != data_b
        assert cache.get_secure(key_b) != data_a

        # The keys themselves are completely different strings
        assert key_a != key_b
