"""Tests for Webhook-Driven Cache Invalidation."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kolay_cli.proxy.webhook import webhook_endpoint, verify_webhook_signature

WEBHOOK_SECRET = "test_webhook_secret_long_enough"

@pytest.fixture
def mock_asgi():
    receive = AsyncMock()
    send = AsyncMock()
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/webhooks/cache-invalidate",
        "headers": []
    }
    return scope, receive, send


def test_verify_webhook_signature():
    body = b'{"tenant_id": "123"}'
    sig = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    
    assert verify_webhook_signature(body, sig, WEBHOOK_SECRET) is True
    assert verify_webhook_signature(body, "wrong", WEBHOOK_SECRET) is False
    assert verify_webhook_signature(body, sig, "wrong_secret") is False


@pytest.mark.asyncio
async def test_webhook_unauthorized_if_signature_invalid(mock_asgi):
    scope, receive, send = mock_asgi
    scope["headers"] = [(b"x-kolayik-signature", b"invalid")]
    
    receive.side_effect = [
        {"type": "http.request", "body": b'{"tenant_id": "123"}'}
    ]
    
    with patch.dict(os.environ, {"WEBHOOK_SECRET": WEBHOOK_SECRET}):
        await webhook_endpoint(scope, receive, send)
    
    # Check 401 response - using simple filter to find the status
    call_args = [call.args[0] for call in send.call_args_list if call.args]
    start_call = next(c for c in call_args if c["type"] == "http.response.start")
    assert start_call["status"] == 401


@pytest.mark.asyncio
@patch("kolay_cli.proxy.webhook.invalidate_raw_tenant")
@patch("kolay_cli.proxy.webhook.semantic_cache.invalidate_tenant")
async def test_webhook_success_purges_cache(mock_sem_invalidate, mock_raw_invalidate, mock_asgi):
    mock_raw_invalidate.return_value = True
    mock_sem_invalidate.return_value = 1
    scope, receive, send = mock_asgi
    body = b'{"tenant_id": "tenant123", "event": "employee_updated"}'
    sig = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    scope["headers"] = [(b"x-kolayik-signature", sig.encode())]
    
    receive.side_effect = [
        {"type": "http.request", "body": body}
    ]
    
    with patch.dict(os.environ, {"WEBHOOK_SECRET": WEBHOOK_SECRET}):
        await webhook_endpoint(scope, receive, send)
    
    # Check purge calls
    mock_raw_invalidate.assert_called_with("tenant123")
    mock_sem_invalidate.assert_called_with("tenant123")
    
    # Check 200 response
    call_args = [call.args[0] for call in send.call_args_list if call.args]
    start_call = next(c for c in call_args if c["type"] == "http.response.start")
    assert start_call["status"] == 200


@pytest.mark.asyncio
@patch("kolay_cli.proxy.webhook.invalidate_raw_tenant")
@patch("kolay_cli.proxy.webhook.semantic_cache.invalidate_tenant")
async def test_webhook_leave_event_spares_raw_cache(mock_sem_invalidate, mock_raw_invalidate, mock_asgi):
    mock_raw_invalidate.return_value = True
    mock_sem_invalidate.return_value = 1
    scope, receive, send = mock_asgi
    body = b'{"tenant_id": "tenant123", "event": "leave_updated"}'
    sig = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    scope["headers"] = [(b"x-kolayik-signature", sig.encode())]
    
    receive.side_effect = [
        {"type": "http.request", "body": body}
    ]
    
    with patch.dict(os.environ, {"WEBHOOK_SECRET": WEBHOOK_SECRET}):
        await webhook_endpoint(scope, receive, send)
    
    # Check purge calls
    mock_raw_invalidate.assert_not_called()
    mock_sem_invalidate.assert_called_with("tenant123")


@pytest.mark.asyncio
async def test_webhook_503_if_no_secret(mock_asgi):
    scope, receive, send = mock_asgi
    with patch.dict(os.environ, {}, clear=True):
        # Ensure it's not in environ
        os.environ.pop("WEBHOOK_SECRET", None)
        await webhook_endpoint(scope, receive, send)
    
    call_args = [call.args[0] for call in send.call_args_list if call.args]
    start_call = next(c for c in call_args if c["type"] == "http.response.start")
    assert start_call["status"] == 503
