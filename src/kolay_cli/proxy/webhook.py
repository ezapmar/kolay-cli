"""Webhook handler for cache invalidation.

Receives mutation events from Kolay IK backend to purge stale caches.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Any

from .cache import invalidate_tenant as invalidate_raw_tenant
from .semantic_cache import semantic_cache

_log = logging.getLogger(__name__)

def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature from the x-kolayik-signature header."""
    if not signature or not secret:
        return False
    
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def webhook_endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
    """ASGI-compatible webhook endpoint for cache invalidation.
    
    Path: /webhooks/cache-invalidate
    Method: POST
    Header: x-kolayik-signature
    Body: {"tenant_id": "...", "event": "..."}
    """
    headers = dict(scope.get("headers", []))
    signature = headers.get(b"x-kolayik-signature", b"").decode("utf-8")
    secret = os.environ.get("WEBHOOK_SECRET")

    if not secret:
        _log.error("WEBHOOK_SECRET is not set. Webhook endpoint is disabled.")
        return await _send_json(send, 503, {"error": "Service Unavailable", "message": "Webhook secret not configured."})

    # Read body
    body = b""
    while True:
        message = await receive()
        if message["type"] == "http.request":
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break
    
    # Verify signature
    if not verify_webhook_signature(body, signature, secret):
        _log.warning("Webhook: Invalid signature received.")
        return await _send_json(send, 401, {"error": "Unauthorized", "message": "Invalid signature."})

    # Parse payload
    try:
        payload = json.loads(body.decode("utf-8"))
        tenant_id = payload.get("tenant_id")
        event = payload.get("event", "unknown")
        
        if not tenant_id:
            return await _send_json(send, 400, {"error": "Bad Request", "message": "Missing tenant_id."})
            
        _log.info("Webhook: Invalidation request for tenant %s (event: %s)", tenant_id[:8], event)
        
        # Action
        # 1. Always purge semantic cache (aggregates)
        sem_purged = semantic_cache.invalidate_tenant(tenant_id)
        
        # 2. Purge raw encrypted cache for non-leave events (employee mutations)
        raw_purged = False
        if event != "leave_updated":
            raw_purged = invalidate_raw_tenant(tenant_id)
            
        return await _send_json(send, 200, {
            "purged": True,
            "tenant_id": tenant_id,
            "event": event,
            "details": {
                "raw_purged": raw_purged,
                "semantic_entries_cleared": sem_purged
            }
        })

    except (json.JSONDecodeError, UnicodeDecodeError):
        return await _send_json(send, 400, {"error": "Bad Request", "message": "Invalid JSON body."})


async def _send_json(send: Any, status: int, data: dict[str, Any]) -> None:
    body = json.dumps(data).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            [b"content-type", b"application/json"],
            [b"content-length", str(len(body)).encode()],
        ],
    })
    await send({"type": "http.response.body", "body": body})
