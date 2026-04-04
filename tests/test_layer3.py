"""Tests for Layer 3 — marketplace manifests and mcp/rag.py context injection."""
import json
import pytest


# ── marketplace.py ──────────────────────────────────────────────────────────────

class TestMarketplaceManifests:
    def test_anthropic_manifest_structure(self):
        from kolay_cli.mcp.marketplace import build_anthropic_manifest
        m = build_anthropic_manifest("https://mcp.kolayik.com")
        assert m["schema_version"] == "v1"
        assert "server" in m
        assert m["server"]["transport"] == "streamable_http"
        assert m["server"]["auth"]["type"] == "api_key"
        assert "privacy_policy" in m["metadata"]

    def test_openai_manifest_structure(self):
        from kolay_cli.mcp.marketplace import build_openai_manifest
        m = build_openai_manifest("https://mcp.kolayik.com")
        assert "name_for_model" in m
        assert m["name_for_model"] == "kolay-ik"
        assert "api" in m
        assert m["api"]["type"] == "openapi"

    def test_openapi_manifest_structure(self):
        from kolay_cli.mcp.marketplace import build_openapi_manifest
        m = build_openapi_manifest("https://mcp.kolayik.com")
        assert m["openapi"] == "3.1.0"
        assert "components" in m
        assert "securitySchemes" in m["components"]
        assert "ApiKeyHeader" in m["components"]["securitySchemes"]

    def test_generate_manifest_dispatch(self):
        from kolay_cli.mcp.marketplace import generate_manifest
        for platform in ("openai", "anthropic", "openapi"):
            m = generate_manifest(platform, "https://mcp.kolayik.com")
            assert isinstance(m, dict)

    def test_generate_manifest_unknown_platform_raises(self):
        from kolay_cli.mcp.marketplace import generate_manifest
        with pytest.raises(ValueError, match="Unknown platform"):
            generate_manifest("unknown_platform", "https://mcp.kolayik.com")

    def test_manifests_are_json_serialisable(self):
        from kolay_cli.mcp.marketplace import PLATFORMS, generate_manifest
        for platform in PLATFORMS:
            m = generate_manifest(platform, "https://mcp.kolayik.com")
            serialised = json.dumps(m)
            assert len(serialised) > 100

    def test_server_url_reflected_in_anthropic(self):
        from kolay_cli.mcp.marketplace import build_anthropic_manifest
        url = "https://custom.example.com/mcp"
        m = build_anthropic_manifest(url)
        assert m["server"]["url"] == url

    def test_openai_manifest_no_trailing_slash(self):
        from kolay_cli.mcp.marketplace import build_openai_manifest
        m = build_openai_manifest("https://mcp.kolayik.com/")
        # URL should be cleaned: no double slash before /openapi.json
        assert "//" not in m["api"]["url"].replace("https://", "")


# ── mcp/rag.py ──────────────────────────────────────────────────────────────────

class TestRagContextInjection:
    def test_retrieve_context_gracefully_returns_empty_on_import_error(self):
        from kolay_cli.mcp.rag import retrieve_context
        import unittest.mock as mock
        with mock.patch.dict("sys.modules", {"kolay_cli.rag.pipeline": None}):
            result = retrieve_context("tenant_x", "remote work policy")
        assert result == []

    def test_inject_rag_context_adds_key_when_chunks_found(self):
        from kolay_cli.mcp.rag import inject_rag_context
        import unittest.mock as mock

        fake_chunks = [
            {"document": "handbook.pdf", "score": 0.92, "text": "Remote work is allowed on Tuesdays."},
        ]

        with mock.patch("kolay_cli.mcp.rag.retrieve_context", return_value=fake_chunks):
            response = {"employees": []}
            enriched = inject_rag_context(response, "tenant_x", "remote work")

        assert "_corporate_context" in enriched
        assert len(enriched["_corporate_context"]["chunks"]) == 1
        assert enriched["_corporate_context"]["chunks"][0]["source"] == "handbook.pdf"

    def test_inject_rag_context_skips_low_relevance(self):
        from kolay_cli.mcp.rag import inject_rag_context
        import unittest.mock as mock

        # Score below 0.4 threshold
        fake_chunks = [
            {"document": "misc.pdf", "score": 0.2, "text": "Irrelevant content."},
        ]

        with mock.patch("kolay_cli.mcp.rag.retrieve_context", return_value=fake_chunks):
            response = {"employees": []}
            enriched = inject_rag_context(response, "tenant_x", "query")

        assert "_corporate_context" not in enriched

    def test_inject_rag_context_returns_response_unchanged_when_no_chunks(self):
        from kolay_cli.mcp.rag import inject_rag_context
        import unittest.mock as mock

        with mock.patch("kolay_cli.mcp.rag.retrieve_context", return_value=[]):
            response = {"result": "ok"}
            enriched = inject_rag_context(response, "tenant_x", "query")

        assert enriched == {"result": "ok"}
        assert "_corporate_context" not in enriched

    def test_inject_truncates_long_excerpts(self):
        from kolay_cli.mcp.rag import inject_rag_context
        import unittest.mock as mock

        long_text = "A" * 1000
        fake_chunks = [{"document": "big.pdf", "score": 0.85, "text": long_text}]

        with mock.patch("kolay_cli.mcp.rag.retrieve_context", return_value=fake_chunks):
            enriched = inject_rag_context({}, "t", "q")

        excerpt = enriched["_corporate_context"]["chunks"][0]["excerpt"]
        assert len(excerpt) <= 500


# ── mcp/gateway.py ──────────────────────────────────────────────────────────────

class TestGatewayModule:
    def test_register_gateway_middleware_callable(self):
        from kolay_cli.mcp.gateway import register_gateway_middleware
        assert callable(register_gateway_middleware)

    def test_is_feature_enabled_standard_defaults(self):
        from kolay_cli.mcp.gateway import _is_feature_enabled
        # In standard profile: MCP_PII_MASKING_ENABLED should default OFF
        import os
        env = {"KOLAY_SECURITY_PROFILE": "standard"}
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("MCP_PII_MASKING_ENABLED", raising=False)
            mp.setenv("KOLAY_SECURITY_PROFILE", "standard")
            assert not _is_feature_enabled("MCP_PII_MASKING_ENABLED", "standard",
                                           default_in_enterprise=True, default_in_standard=False)

    def test_is_feature_enabled_enterprise_defaults(self):
        from kolay_cli.mcp.gateway import _is_feature_enabled
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("MCP_PII_MASKING_ENABLED", raising=False)
            assert _is_feature_enabled("MCP_PII_MASKING_ENABLED", "enterprise",
                                       default_in_enterprise=True, default_in_standard=False)

    def test_is_feature_enabled_env_override(self):
        from kolay_cli.mcp.gateway import _is_feature_enabled
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("MCP_PII_MASKING_ENABLED", "1")
            # Even in standard profile, explicit env var wins
            assert _is_feature_enabled("MCP_PII_MASKING_ENABLED", "standard",
                                       default_in_enterprise=True, default_in_standard=False)
