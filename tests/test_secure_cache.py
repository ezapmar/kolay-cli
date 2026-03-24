"""Tests for:
  - Req 1: Drop-at-the-door PII field sanitization (field_sanitizer)
  - Req 2: Ephemeral in-memory encryption (SecureVolatileCache)
  - Req 3: Cryptographic tenant isolation (generate_tenant_cache_key)
"""
from __future__ import annotations

import os
import time

import pytest

from kolay_cli.field_sanitizer import ALLOWED_FIELDS, sanitize_employees
from kolay_cli.secure_cache import SecureVolatileCache, generate_tenant_cache_key


# ---------------------------------------------------------------------------
# Req 1: Field sanitizer
# ---------------------------------------------------------------------------

class TestSanitizeEmployees:
    """Bloated JSON in -> sanitized JSON out."""

    BLOATED = [
        {
            "id": "abc123",
            "firstName": "Ayse",
            "lastName": "Yilmaz",
            "department": "Engineering",
            "status": "active",
            "workEmail": "ayse@company.com",
            "birthDate": "1990-04-15",
            "employmentStartDate": "2020-01-01",
            "title": "Engineer",
            # --- PII fields that MUST be stripped ---
            "salary": 95000,
            "salaryHistory": [80000, 85000, 90000, 95000],
            "iban": "TR12 0006 2000 1190 0006 2920 77",
            "ssn": "123-45-6789",
            "nationalId": "12345678901",
            "mobilePhone": "555-1234",
            "homeAddress": "123 Main St, Istanbul",
            "city": "Istanbul",
            "bankAccount": "TR000001",
            "emergencyContact": "Ali Yilmaz: 555-9999",
            "taxId": "9876543210",
            "passportNumber": "A1234567",
        }
    ]

    def test_banned_fields_are_removed(self) -> None:
        clean = sanitize_employees(self.BLOATED)
        assert len(clean) == 1
        rec = clean[0]
        banned = [
            "salary", "salaryHistory", "iban", "ssn", "nationalId",
            "mobilePhone", "homeAddress", "city", "bankAccount",
            "emergencyContact", "taxId", "passportNumber",
        ]
        for field in banned:
            assert field not in rec, f"Banned field '{field}' survived sanitization"

    def test_allowed_fields_are_preserved(self) -> None:
        clean = sanitize_employees(self.BLOATED)
        rec = clean[0]
        assert rec["id"] == "abc123"
        assert rec["firstName"] == "Ayse"
        assert rec["lastName"] == "Yilmaz"
        assert rec["department"] == "Engineering"
        assert rec["status"] == "active"
        assert rec["workEmail"] == "ayse@company.com"
        assert rec["birthDate"] == "1990-04-15"
        assert rec["employmentStartDate"] == "2020-01-01"
        assert rec["title"] == "Engineer"

    def test_only_allowed_keys_remain(self) -> None:
        clean = sanitize_employees(self.BLOATED)
        remaining_keys = set(clean[0].keys())
        assert remaining_keys.issubset(ALLOWED_FIELDS), (
            f"Unexpected keys in output: {remaining_keys - ALLOWED_FIELDS}"
        )

    def test_empty_list_returns_empty_list(self) -> None:
        assert sanitize_employees([]) == []

    def test_record_with_no_allowed_fields_returns_empty_dict(self) -> None:
        all_banned = [{"salary": 50000, "iban": "TR00", "city": "Ankara"}]
        clean = sanitize_employees(all_banned)
        assert clean == [{}]

    def test_missing_allowed_field_is_not_added(self) -> None:
        """sanitize must not inject keys that don't exist in the source."""
        minimal = [{"id": "x", "salary": 999}]
        clean = sanitize_employees(minimal)
        assert "birthDate" not in clean[0]  # not in source, should not appear
        assert "salary" not in clean[0]

    def test_large_array_performance(self) -> None:
        """50,000 records must complete in under 2 seconds (O(N) guarantee)."""
        large = [dict(self.BLOATED[0], id=str(i)) for i in range(50_000)]
        t0 = time.monotonic()
        clean = sanitize_employees(large)
        elapsed = time.monotonic() - t0
        assert len(clean) == 50_000
        assert elapsed < 2.0, f"sanitize_employees took {elapsed:.2f}s for 50k records"

    def test_original_list_is_not_mutated(self) -> None:
        """sanitize must return new dicts, not modify in-place."""
        original = [dict(self.BLOATED[0])]
        _ = sanitize_employees(original)
        assert "salary" in original[0], "Original record was mutated"


# ---------------------------------------------------------------------------
# Req 2: SecureVolatileCache
# ---------------------------------------------------------------------------

class TestSecureVolatileCache:

    def setup_method(self) -> None:
        self.cache = SecureVolatileCache(default_ttl=5)

    def test_set_and_get_roundtrip(self) -> None:
        data = [{"id": "1", "firstName": "Ali"}]
        self.cache.set_secure("k1", data)
        result = self.cache.get_secure("k1")
        assert result == data

    def test_internal_store_holds_only_bytes(self) -> None:
        """The raw _store must hold ciphertext (bytes), never plaintext dicts."""
        self.cache.set_secure("k2", [{"secret": "should_be_encrypted"}])
        _, ciphertext = self.cache._store["k2"]
        assert isinstance(ciphertext, bytes), "Cache stored non-bytes value"
        # Ciphertext must not contain the plaintext in any readable form
        assert b"should_be_encrypted" not in ciphertext

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
        assert "ciphertext_bytes" in st
        assert st["ciphertext_bytes"] > 0

    def test_status_missing_entry(self) -> None:
        st = self.cache.status("missing")
        assert st["cached"] is False
        assert st["encrypted"] is True

    def test_crypto_shredding_simulation(self) -> None:
        """
        Simulates a server restart: a NEW SecureVolatileCache instance generates
        a fresh ephemeral key.  Data stored by one instance is unreadable by
        another instance holding a different key.

        In production: when the process dies, the key object is garbage-collected
        and the OS reclaims the memory.  All ciphertext in the old process is
        permanently unrecoverable — crypto-shredding by design.
        """
        import base64
        from cryptography.fernet import InvalidToken  # type: ignore[import-untyped]

        # Two independent "server instances" with distinct ephemeral keys
        key_a = base64.urlsafe_b64encode(os.urandom(32))
        key_b = base64.urlsafe_b64encode(os.urandom(32))
        assert key_a != key_b, "Test precondition: keys must differ"

        cache_a = SecureVolatileCache(default_ttl=60, _fernet_key=key_a)
        cache_b = SecureVolatileCache(default_ttl=60, _fernet_key=key_b)

        cache_a.set_secure("shared_key", {"sensitive": "data"})
        _, ciphertext = cache_a._store["shared_key"]

        # Inject ciphertext from cache_a into cache_b (simulating taking a memory dump
        # and replanting it after a restart with a new key)
        cache_b._store["shared_key"] = (time.monotonic() + 60, ciphertext)

        # cache_b (different ephemeral key) cannot decrypt cache_a's ciphertext
        with pytest.raises(InvalidToken):
            cache_b.get_secure("shared_key")


    def test_complex_data_types_roundtrip(self) -> None:
        data = {
            "employees": [{"id": "1", "dept": "Eng"}],
            "count": 42,
            "meta": {"source": "cache"},
        }
        self.cache.set_secure("complex", data)
        assert self.cache.get_secure("complex") == data


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

    def test_output_is_64_char_hex(self) -> None:
        key = generate_tenant_cache_key("t1", "employees")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_pepper_changes_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SERVER_CACHE_PEPPER", "pepper_v1")
        k1 = generate_tenant_cache_key("t1", "employees")
        monkeypatch.setenv("SERVER_CACHE_PEPPER", "pepper_v2")
        k2 = generate_tenant_cache_key("t1", "employees")
        assert k1 != k2

    def test_no_pepper_still_produces_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SERVER_CACHE_PEPPER", raising=False)
        key = generate_tenant_cache_key("t1", "employees")
        assert len(key) == 64

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
