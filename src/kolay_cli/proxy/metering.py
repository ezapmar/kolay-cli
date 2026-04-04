"""Usage metering and billing event emission for Kolay MCP API Gateway."""
import json
import logging
import asyncio
import os
import httpx
from typing import Any

from ..mcp.adapter import Middleware, CallNext

_log = logging.getLogger(__name__)

async def _emit_billing_webhook(tenant_id: str, tool_name: str, response_size: int, duration_ms: float) -> None:
    """Fire-and-forget webhook to Kolay billing service."""
    webhook_url = os.environ.get("BILLING_WEBHOOK_URL")
    if not webhook_url:
        return
        
    secret = os.environ.get("BILLING_WEBHOOK_SECRET", "")
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
        
    payload = {
        "tenant_id": tenant_id,
        "tool": tool_name,
        "response_bytes": response_size,
        "duration_ms": duration_ms,
        "event_type": "mcp_tool_call"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=payload, headers=headers, timeout=5.0)
            if resp.status_code >= 400:
                _log.warning(f"Billing webhook failed with status {resp.status_code}")
    except Exception as exc:
        _log.warning(f"Failed to emit billing event for {tenant_id}: {exc}")

class UsageMeteringMiddleware(Middleware):
    """Middleware that measures tool usage (call count, response size) 
    and emits billing events synchronously or asynchronously.
    """
    
    async def __call__(self, ctx: Any, call_next: CallNext) -> Any:
        import time
        from .auth import get_tenant_id
        from ..security import KOLAY_TOKEN_CTX
        
        token = KOLAY_TOKEN_CTX.get()
        tenant_id = get_tenant_id(token)
        
        req = getattr(ctx, "request", None)
        tool_name = getattr(req, "name", "unknown") if req else "unknown"
        
        t0 = time.monotonic()
        result = await call_next(ctx)
        duration_ms = (time.monotonic() - t0) * 1000.0
        
        # Estimate size by serializing to JSON, similar to what FastMCP does
        size_bytes = 0
        if result and hasattr(result, "model_dump_json"):
            try:
                size_bytes = len(result.model_dump_json().encode("utf-8"))
            except Exception:
                pass
        
        # Emit billing event asynchronously so we don't block the response
        asyncio.create_task(_emit_billing_webhook(
            tenant_id=tenant_id, 
            tool_name=tool_name, 
            response_size=size_bytes, 
            duration_ms=round(duration_ms, 2)
        ))
        
        return result

