"""Layer 1 Gateway Concerns — extracted per platform.md §7.3.

This module owns the gateway-level middleware chain:
  - Tenant identification
  - Rate limiting (per-tenant)
  - Usage metering + billing event emission
  - Request/response logging

All concerns operate via FastMCP middleware so they are transparent to
individual tool implementations. Tools never import from this module;
mcp_server.py is the only consumer.
"""
from __future__ import annotations

import os
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

_log = logging.getLogger(__name__)


def _is_feature_enabled(
    env_var: str,
    profile: str,
    default_in_enterprise: bool = False,
    default_in_standard: bool = False,
) -> bool:
    val = os.environ.get(env_var)
    if val is not None:
        return val.lower() in ("1", "true", "yes")
    return default_in_enterprise if profile == "enterprise" else default_in_standard


def register_gateway_middleware(mcp: "FastMCP") -> None:
    """Attach all Layer 1 gateway middleware to the given FastMCP instance.

    Call this AFTER tool registration and BEFORE starting the server.
    The order here determines the middleware wrapping order (outermost first).
    """
    from ..mcp.adapter import (
        ErrorHandlingMiddleware,
        SlidingWindowRateLimitingMiddleware,
        TimingMiddleware,
        ResponseLimitingMiddleware,
        PingMiddleware,
    )

    profile = os.environ.get("KOLAY_SECURITY_PROFILE", "standard").lower()

    # 1. Error handler — outermost, catches everything
    mcp.add_middleware(ErrorHandlingMiddleware(include_traceback=False, transform_errors=True))

    # 2. Per-tenant rate limiting
    rl_enabled = _is_feature_enabled(
        "MCP_RATE_LIMIT_ENABLED", profile,
        default_in_enterprise=True, default_in_standard=True
    )
    if rl_enabled:
        from ..proxy.auth import get_tenant_id as _get_tenant_id
        from ..security import KOLAY_TOKEN_CTX as _TOKEN_CTX

        def _get_client_id(ctx) -> str:  # noqa: ANN001
            token = _TOKEN_CTX.get()
            return _get_tenant_id(token)

        per_min = int(os.environ.get("MCP_RATE_LIMIT_PER_MINUTE", "30"))
        mcp.add_middleware(SlidingWindowRateLimitingMiddleware(
            max_requests=per_min,
            window_minutes=1,
            get_client_id=_get_client_id,
        ))
        _log.info("Gateway: rate limiting enabled (%d req/min per tenant)", per_min)

    # 2.5. RBAC Tool Provisioning (opt-in)
    if os.environ.get("MCP_RBAC_ENABLED", "").lower() in ("1", "true", "yes"):
        from ..proxy.rbac import RBACToolFilterMiddleware
        mcp.add_middleware(RBACToolFilterMiddleware())
        _log.info("Gateway: RBAC tool filter enabled")

    # 3. Request timing
    mcp.add_middleware(TimingMiddleware())

    # 3.5. Usage metering + billing webhook emission
    from ..proxy.metering import UsageMeteringMiddleware
    mcp.add_middleware(UsageMeteringMiddleware())
    _log.info("Gateway: usage metering enabled")

    # 4. Response size guard — 500 KB hard cap
    mcp.add_middleware(ResponseLimitingMiddleware(max_size=500_000))

    # 4.5. PII Masking — enterprise default ON, standard default OFF
    pii_enabled = _is_feature_enabled(
        "MCP_PII_MASKING_ENABLED", profile,
        default_in_enterprise=True, default_in_standard=False
    )
    if pii_enabled:
        from ..pii_masker import PIIMaskingMiddleware
        mcp.add_middleware(PIIMaskingMiddleware())
        _log.info("Gateway: PII masking enabled")

    # 5. SSE keep-alive ping (prevents proxy timeouts)
    mcp.add_middleware(PingMiddleware(interval_ms=30_000))

    _log.info("Gateway: middleware stack registered (profile=%s)", profile)
