"""Tests for JIT RBAC tool provisioning."""
from __future__ import annotations

import jwt
import pytest
from unittest.mock import MagicMock, patch

from kolay_cli.proxy.rbac import (
    resolve_user_role, is_tool_allowed, RBACToolFilterMiddleware, ROLE_TAG_ALLOWLIST
)
from kolay_cli.security import KOLAY_TOKEN_CTX

# Mock secret for JWT generation in tests
JWT_SECRET = "test_secret_long_enough_for_sha256_32bytes"

def create_test_token(role: str | None = None) -> str:
    payload = {}
    if role:
        payload["user_role"] = role
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def test_resolve_role_from_jwt():
    token = create_test_token("hr_admin")
    reset_token = KOLAY_TOKEN_CTX.set(token)
    try:
        assert resolve_user_role() == "hr_admin"
    finally:
        KOLAY_TOKEN_CTX.reset(reset_token)


def test_resolve_role_default_employee():
    # No token
    reset_token = KOLAY_TOKEN_CTX.set(None)
    try:
        assert resolve_user_role() == "employee"
    finally:
        KOLAY_TOKEN_CTX.reset(reset_token)


def test_resolve_role_unknown_falls_to_employee():
    token = create_test_token("intern")
    reset_token = KOLAY_TOKEN_CTX.set(token)
    try:
        assert resolve_user_role() == "employee"
    finally:
        KOLAY_TOKEN_CTX.reset(reset_token)


def test_is_tool_allowed_employee():
    assert is_tool_allowed({"read"}, "employee") is True
    assert is_tool_allowed({"session"}, "employee") is True
    assert is_tool_allowed({"write"}, "employee") is False
    assert is_tool_allowed({"destructive"}, "employee") is False
    assert is_tool_allowed({"admin"}, "employee") is False


def test_is_tool_allowed_hr_manager():
    assert is_tool_allowed({"read"}, "hr_manager") is True
    assert is_tool_allowed({"write"}, "hr_manager") is True
    assert is_tool_allowed({"analytics"}, "hr_manager") is True
    assert is_tool_allowed({"destructive"}, "hr_manager") is False
    assert is_tool_allowed({"admin"}, "hr_manager") is False


def test_is_tool_allowed_hr_admin():
    assert is_tool_allowed({"read"}, "hr_admin") is True
    assert is_tool_allowed({"write"}, "hr_admin") is True
    assert is_tool_allowed({"destructive"}, "hr_admin") is True
    assert is_tool_allowed({"admin"}, "hr_admin") is True


@pytest.mark.asyncio
async def test_rbac_middleware_list_tools_filtering():
    middleware = RBACToolFilterMiddleware()
    
    # Mock tool list
    class MockTool:
        def __init__(self, name, tags):
            self.name = name
            self.tags = tags

    tools = [
        MockTool("read_tool", {"read"}),
        MockTool("write_tool", {"write"}),
        MockTool("admin_tool", {"admin"}),
    ]

    async def next_call(ctx):
        return tools

    ctx = MagicMock()
    ctx.operation = "list_tools"
    
    # Test as employee
    token = create_test_token("employee")
    reset_token = KOLAY_TOKEN_CTX.set(token)
    try:
        filtered = await middleware(ctx, next_call)
        assert len(filtered) == 1
        assert filtered[0].name == "read_tool"
    finally:
        KOLAY_TOKEN_CTX.reset(reset_token)


@pytest.mark.asyncio
async def test_rbac_middleware_call_tool_403():
    middleware = RBACToolFilterMiddleware()
    
    async def next_call(ctx):
        return {"ok": True}

    # Mock server tools registration
    class MockTool:
        def __init__(self, tags):
            self.tags = tags

    ctx = MagicMock()
    ctx.operation = "call_tool"
    ctx.request.params = {"name": "admin_tool"}
    
    mock_server = MagicMock()
    mock_server.tools = {"admin_tool": MockTool({"admin"})}
    ctx.server = mock_server

    # Test call as employee -> 403
    token = create_test_token("employee")
    reset_token = KOLAY_TOKEN_CTX.set(token)
    try:
        response = await middleware(ctx, next_call)
        assert response["error"] is True
        assert response["code"] == 403
        assert "Access denied" in response["message"]
    finally:
        KOLAY_TOKEN_CTX.reset(reset_token)
