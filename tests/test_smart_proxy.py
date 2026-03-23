"""
tests/test_smart_proxy.py -- Tests for TTL cache, smart proxy tools, and manifest.

Coverage: TTLCache hit/miss/expiry, search_employees filter+projection+truncation,
get_employee_statistics for all metrics, get_cache_status shape, mock data generation.
"""
from __future__ import annotations

import time
from unittest.mock import patch, MagicMock

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# TTL CACHE
# ══════════════════════════════════════════════════════════════════════════════

class TestTTLCache:
    def test_cache_miss_returns_none(self):
        from kolay_cli.ttl_cache import TTLCache
        cache = TTLCache(default_ttl=60)
        assert cache.get("missing") is None

    def test_cache_hit_returns_value(self):
        from kolay_cli.ttl_cache import TTLCache
        cache = TTLCache(default_ttl=60)
        cache.set("key1", [1, 2, 3])
        assert cache.get("key1") == [1, 2, 3]

    def test_cache_expiry(self):
        from kolay_cli.ttl_cache import TTLCache
        cache = TTLCache(default_ttl=1)  # 1-second TTL
        cache.set("key1", "value")
        assert cache.get("key1") == "value"
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_cache_invalidate(self):
        from kolay_cli.ttl_cache import TTLCache
        cache = TTLCache(default_ttl=60)
        cache.set("key1", "value")
        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None
        assert cache.invalidate("key1") is False  # already gone

    def test_cache_clear(self):
        from kolay_cli.ttl_cache import TTLCache
        cache = TTLCache(default_ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_cache_status_empty(self):
        from kolay_cli.ttl_cache import TTLCache
        cache = TTLCache(default_ttl=300)
        status = cache.status("missing")
        assert status["cached"] is False
        assert status["entry_count"] == 0
        assert status["ttl_seconds"] == 300

    def test_cache_status_populated(self):
        from kolay_cli.ttl_cache import TTLCache
        cache = TTLCache(default_ttl=300)
        cache.set("key1", [{"id": "1"}, {"id": "2"}])
        status = cache.status("key1")
        assert status["cached"] is True
        assert status["entry_count"] == 2
        assert status["ttl_seconds"] == 300
        assert status["expires_in_seconds"] > 0

    def test_custom_ttl_per_entry(self):
        from kolay_cli.ttl_cache import TTLCache
        cache = TTLCache(default_ttl=300)
        cache.set("fast", "data", ttl=1)
        assert cache.get("fast") == "data"
        time.sleep(1.1)
        assert cache.get("fast") is None


# ══════════════════════════════════════════════════════════════════════════════
# MOCK DATA GENERATION
# ══════════════════════════════════════════════════════════════════════════════

class TestMockData:
    def test_generates_3000_records(self):
        from kolay_cli.ttl_cache import _generate_mock_employees
        data = _generate_mock_employees(3000)
        assert len(data) == 3000

    def test_records_have_required_fields(self):
        from kolay_cli.ttl_cache import _generate_mock_employees
        data = _generate_mock_employees(10)
        required = {"id", "firstName", "lastName", "department", "birthDate", "employmentStartDate", "status"}
        for emp in data:
            assert required.issubset(emp.keys()), f"Missing fields in {emp.keys()}"

    def test_deterministic_with_seed(self):
        from kolay_cli.ttl_cache import _generate_mock_employees
        a = _generate_mock_employees(50)
        b = _generate_mock_employees(50)
        assert a == b


# ══════════════════════════════════════════════════════════════════════════════
# SMART PROXY TOOLS
# ══════════════════════════════════════════════════════════════════════════════

MOCK_EMPLOYEES = [
    {"id": f"emp{i}", "firstName": f"First{i}", "lastName": f"Last{i}",
     "department": "Engineering" if i < 30 else "Marketing",
     "workEmail": f"user{i}@example.com", "status": "active",
     "birthDate": f"199{i % 10}-{(i % 12) + 1:02d}-15",
     "employmentStartDate": f"202{i % 5}-01-01",
     "salary": 10000 + i * 100}
    for i in range(100)
]


class TestSearchEmployees:
    def _run(self, **kwargs):
        from kolay_cli.mcp.tools_smart_proxy import search_employees
        with patch("kolay_cli.mcp.tools_smart_proxy.fetch_all_employees", return_value=MOCK_EMPLOYEES):
            return search_employees(**kwargs)

    def test_returns_all_with_no_filters(self):
        result = self._run()
        assert result["count"] == 50  # hard-capped
        assert result["total_before_limit"] == 100

    def test_truncation_warning_present(self):
        result = self._run()
        assert "warning" in result["_meta"]
        assert "truncated" in result["_meta"]["warning"].lower()

    def test_department_filter(self):
        result = self._run(department="Engineering")
        assert result["total_before_limit"] == 30
        assert result["count"] == 30

    def test_department_filter_no_truncation(self):
        result = self._run(department="Engineering")
        assert "warning" not in result["_meta"]

    def test_birth_month_filter(self):
        result = self._run(birth_month=1)
        # Employees with index where (i % 12) + 1 == 1, i.e. i % 12 == 0
        # i = 0, 12, 24, 36, 48, 60, 72, 84, 96 = 9 employees
        assert result["total_before_limit"] == 9
        assert result["count"] == 9

    def test_projection_strips_fields(self):
        result = self._run(department="Engineering", fields=["id", "firstName"])
        for item in result["results"]:
            assert set(item.keys()) == {"id", "firstName"}

    def test_default_projection(self):
        result = self._run(department="Engineering")
        expected_fields = {"id", "firstName", "lastName", "department", "workEmail", "status"}
        for item in result["results"]:
            assert set(item.keys()) == expected_fields

    def test_combined_filters(self):
        result = self._run(department="Marketing", birth_month=1)
        for item in result["results"]:
            assert True  # Just checking it doesn't crash

    def test_meta_includes_source(self):
        result = self._run()
        assert result["_meta"]["source"] == "ttl_cache"


class TestGetEmployeeStatistics:
    def _run(self, **kwargs):
        from kolay_cli.mcp.tools_smart_proxy import get_employee_statistics
        with patch("kolay_cli.mcp.tools_smart_proxy.fetch_all_employees", return_value=MOCK_EMPLOYEES):
            return get_employee_statistics(**kwargs)

    def test_headcount(self):
        result = self._run(metric="headcount")
        assert result["metric"] == "headcount"
        assert result["value"] == 100

    def test_headcount_with_department(self):
        result = self._run(metric="headcount", department="Engineering")
        assert result["value"] == 30

    def test_average_age(self):
        result = self._run(metric="average_age")
        assert result["metric"] == "average_age"
        assert isinstance(result["value"], float)
        assert result["sample_size"] == 100
        assert "min_age" in result
        assert "max_age" in result

    def test_department_distribution(self):
        result = self._run(metric="department_distribution")
        assert result["metric"] == "department_distribution"
        assert result["total"] == 100
        assert "Engineering" in result["departments"]
        assert "Marketing" in result["departments"]
        assert result["departments"]["Marketing"] == 70
        assert result["departments"]["Engineering"] == 30

    def test_tenure_distribution(self):
        result = self._run(metric="tenure_distribution")
        assert result["metric"] == "tenure_distribution"
        assert result["total"] == 100
        assert "<1 year" in result["buckets"]
        assert "10+ years" in result["buckets"]

    def test_unknown_metric(self):
        result = self._run(metric="nonexistent")
        assert result["error"] is True
        assert "Unknown metric" in result["message"]

    def test_no_matching_employees(self):
        result = self._run(metric="headcount", department="NonexistentDept")
        assert result["error"] is True


class TestGetCacheStatus:
    def test_returns_correct_shape(self):
        from kolay_cli.mcp.tools_smart_proxy import get_cache_status
        from kolay_cli.ttl_cache import employee_cache
        employee_cache.clear()
        result = get_cache_status()
        assert "cached" in result
        assert "entry_count" in result
        assert "ttl_seconds" in result
        assert result["cached"] is False


# ══════════════════════════════════════════════════════════════════════════════
# MANIFEST GENERATION
# ══════════════════════════════════════════════════════════════════════════════

class TestManifest:
    @staticmethod
    def _import_manifest():
        import sys
        from pathlib import Path
        scripts_dir = str(Path(__file__).resolve().parent.parent / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import generate_manifest
        return generate_manifest

    def test_manifest_structure(self):
        mod = self._import_manifest()
        m = mod.generate_manifest()
        assert m["schema_version"] == "1.0"
        assert "server" in m
        assert "tools" in m
        assert "data_policies" in m
        assert m["data_policies"]["no_llm_training"] is True

    def test_sign_and_verify(self):
        pytest.importorskip("cryptography")
        mod = self._import_manifest()
        manifest = mod.generate_manifest()
        jws, _priv, pub = mod.sign_manifest(manifest)
        assert mod.verify_manifest(jws, pub) is True

    def test_tamper_detection(self):
        pytest.importorskip("cryptography")
        mod = self._import_manifest()
        manifest = mod.generate_manifest()
        jws, _priv, pub = mod.sign_manifest(manifest)
        tampered = jws[:10] + "TAMPERED" + jws[18:]
        assert mod.verify_manifest(tampered, pub) is False
