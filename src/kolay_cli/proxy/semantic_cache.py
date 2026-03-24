"""Semantic Result Caching for analytical MCP tools.

Reduces CPU usage and redundant database/API calls by caching the final
computed results of expensive analytical operations (headcounts, averages, etc.)
scoped by tenant and query parameters.
"""
from __future__ import annotations

import functools
import hashlib
import hmac
import json
import logging
import os
import threading
import time
from typing import Any, Callable, TypeVar, cast

from ..security import KOLAY_TOKEN_CTX
from ..rate_limiter import token_key

_log = logging.getLogger(__name__)

# Type variable for the decorated function
F = TypeVar("F", bound=Callable[..., Any])

class SemanticCache:
    """Thread-safe in-memory cache with lazy TTL eviction."""
    
    def __init__(self, default_ttl: int = 900) -> None:
        self._store: dict[str, tuple[float, Any]] = {}  # key -> (expires_at, result)
        self._lock = threading.Lock()
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        """Fetch result if present and not expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            
            expires_at, result = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                self.misses += 1
                return None
            
            self.hits += 1
            return result

    def set(self, key: str, result: Any, ttl: int | None = None) -> None:
        """Store result with TTL."""
        with self._lock:
            expires_at = time.monotonic() + (ttl if ttl is not None else self.default_ttl)
            self._store[key] = (expires_at, result)

    def invalidate_tenant(self, tenant_id_prefix: str) -> int:
        """Remove all entries starting with the given tenant_id_prefix.
        
        Returns the number of entries removed.
        """
        count = 0
        with self._lock:
            # Create a list of keys to delete to avoid dictionary mutation during iteration
            to_delete = [
                k for k in self._store 
                if k.startswith(tenant_id_prefix)
            ]
            for k in to_delete:
                del self._store[k]
                count += 1
        return count

    def status(self) -> dict[str, Any]:
        """Return diagnostic info."""
        with self._lock:
            # Clean expired first for more accurate count
            now = time.monotonic()
            expired = [k for k, (exp, _) in self._store.items() if now > exp]
            for k in expired:
                del self._store[k]
                
            return {
                "entry_count": len(self._store),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{(self.hits / (self.hits + self.misses) * 100):.1f}%" if (self.hits + self.misses) > 0 else "0.0%",
            }


# Global singleton instance
semantic_cache = SemanticCache(default_ttl=900)


def _make_cache_key(tenant_id: str, tool_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Generate a deterministic 64-char hex key.
    
    HMAC-SHA256(pepper, f"{tenant_id}:{tool_name}:{sorted_json_params}")
    """
    pepper = os.environ.get("SERVER_CACHE_PEPPER", "default_semantic_pepper")
    
    # Normalize arguments to a sorted JSON string for deterministic hashing
    params = {
        "args": list(args),
        "kwargs": kwargs
    }
    params_json = json.dumps(params, sort_keys=True, default=str)
    
    msg = f"{tenant_id}:{tool_name}:{params_json}".encode("utf-8")
    return hmac.new(pepper.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def semantic_cached(ttl: int | None = 900) -> Callable[[F], F]:
    """Decorator to cache analytical tool results.
    
    Extracts tenant_id from KOLAY_TOKEN_CTX. Skip caching if no token.
    Only caches if MCP_SEMANTIC_CACHE_ENABLED=true.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            enabled = os.environ.get("MCP_SEMANTIC_CACHE_ENABLED", "").lower() in ("1", "true", "yes")
            if not enabled:
                return func(*args, **kwargs)

            # Get tenant_id
            token = KOLAY_TOKEN_CTX.get()
            if not token:
                # No token (e.g. stdio mode without auth), skip cache for safety
                return func(*args, **kwargs)
            
            tenant_id = token_key(token)
            cache_key = _make_cache_key(tenant_id, func.__name__, args, kwargs)
            
            # Lookup
            cached_result = semantic_cache.get(cache_key)
            if cached_result is not None:
                _log.debug("Semantic Cache HIT: %s (tenant: %s)", func.__name__, tenant_id[:8])
                return cached_result
            
            # Miss path
            _log.debug("Semantic Cache MISS: %s (tenant: %s)", func.__name__, tenant_id[:8])
            result = func(*args, **kwargs)
            
            # Only cache if not an error response
            if isinstance(result, dict) and result.get("error"):
                return result
                
            semantic_cache.set(cache_key, result, ttl=ttl)
            return result
            
        return cast(F, wrapper)
    return decorator
