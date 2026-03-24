"""Tests for Semantic Result Cache."""
from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import pytest
from kolay_cli.proxy.semantic_cache import semantic_cache, semantic_cached, _make_cache_key
from kolay_cli.security import KOLAY_TOKEN_CTX

@pytest.fixture(autouse=True)
def enable_cache():
    with patch.dict(os.environ, {"MCP_SEMANTIC_CACHE_ENABLED": "true"}):
        yield

@pytest.fixture(autouse=True)
def clear_cache():
    semantic_cache.hits = 0
    semantic_cache.misses = 0
    semantic_cache._store.clear()
    yield

def test_cache_key_determinism():
    key1 = _make_cache_key("tenant1", "tool1", (1, 2), {"a": 3})
    key2 = _make_cache_key("tenant1", "tool1", (1, 2), {"a": 3})
    key3 = _make_cache_key("tenant1", "tool1", (1, 2), {"a": 4})
    
    assert key1 == key2
    assert key1 != key3


def test_cache_miss_executes_function():
    mock_func = MagicMock(return_value={"result": 42})
    mock_func.__name__ = "mock_func"
    decorated = semantic_cached(ttl=60)(mock_func)
    
    token_reset = KOLAY_TOKEN_CTX.set("fake_token")
    try:
        # First call: MISS
        res1 = decorated(1, a=2)
        assert res1 == {"result": 42}
        assert mock_func.call_count == 1
        assert semantic_cache.misses == 1
        assert semantic_cache.hits == 0
    finally:
        KOLAY_TOKEN_CTX.reset(token_reset)


def test_cache_hit_returns_cached():
    mock_func = MagicMock(return_value={"result": 42})
    mock_func.__name__ = "mock_func"
    decorated = semantic_cached(ttl=60)(mock_func)
    
    token_reset = KOLAY_TOKEN_CTX.set("fake_token")
    try:
        # First call: MISS
        decorated(1, a=2)
        # Second call: HIT
        res2 = decorated(1, a=2)
        assert res2 == {"result": 42}
        assert mock_func.call_count == 1  # Still 1
        assert semantic_cache.hits == 1
    finally:
        KOLAY_TOKEN_CTX.reset(token_reset)


def test_different_tenants_different_keys():
    mock_func = MagicMock(side_effect=[{"r": 1}, {"r": 2}])
    mock_func.__name__ = "mock_func"
    decorated = semantic_cached(ttl=60)(mock_func)
    
    # Tenant 1
    token_reset1 = KOLAY_TOKEN_CTX.set("token1")
    try:
        res1 = decorated(1)
        assert res1 == {"r": 1}
    finally:
        KOLAY_TOKEN_CTX.reset(token_reset1)
        
    # Tenant 2
    token_reset2 = KOLAY_TOKEN_CTX.set("token2")
    try:
        res2 = decorated(1)
        assert res2 == {"r": 2}
        assert mock_func.call_count == 2
    finally:
        KOLAY_TOKEN_CTX.reset(token_reset2)


def test_ttl_expiry():
    mock_func = MagicMock(return_value={"result": 42})
    mock_func.__name__ = "mock_func"
    decorated = semantic_cached(ttl=0.01)(mock_func)
    
    token_reset = KOLAY_TOKEN_CTX.set("fake_token")
    try:
        decorated(1)
        assert mock_func.call_count == 1
        
        time.sleep(0.02)
        
        decorated(1)
        assert mock_func.call_count == 2
    finally:
        KOLAY_TOKEN_CTX.reset(token_reset)


def test_cache_disabled():
    mock_func = MagicMock(return_value={"result": 42})
    mock_func.__name__ = "mock_func"
    decorated = semantic_cached(ttl=60)(mock_func)
    
    token_reset = KOLAY_TOKEN_CTX.set("fake_token")
    try:
        with patch.dict(os.environ, {"MCP_SEMANTIC_CACHE_ENABLED": "false"}):
            decorated(1)
            decorated(1)
            assert mock_func.call_count == 2
            assert semantic_cache.hits == 0
    finally:
        KOLAY_TOKEN_CTX.reset(token_reset)


def test_no_token_skips_cache():
    mock_func = MagicMock(return_value={"result": 42})
    mock_func.__name__ = "mock_func"
    decorated = semantic_cached(ttl=60)(mock_func)
    
    token_reset = KOLAY_TOKEN_CTX.set(None)
    try:
        decorated(1)
        decorated(1)
        assert mock_func.call_count == 2
        assert semantic_cache.hits == 0
    finally:
        KOLAY_TOKEN_CTX.reset(token_reset)

def test_cache_status():
    semantic_cache.set("key1", "val1", ttl=60)
    semantic_cache.hits = 5
    semantic_cache.misses = 5
    status = semantic_cache.status()
    assert status["entry_count"] == 1
    assert status["hit_rate"] == "50.0%"
