"""Tests for the PII masking middleware and logic."""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock

from kolay_cli.pii_masker import (
    mask_value,
    mask_dict,
    generate_pseudonym,
    _STATIC_FIELDS,
    PIIMaskingMiddleware,
)
from mcp.types import TextContent

class MockToolResult:
    def __init__(self, content):
        self.content = content

class MockMiddlewareContext:
    pass


def test_pseudonym_deterministic():
    """Generating a pseudonym for the same string always yields the same result."""
    p1 = generate_pseudonym("Ahmet")
    p2 = generate_pseudonym("Ahmet")
    p3 = generate_pseudonym("ahmet")  # case-insensitive
    assert p1 == p2 == p3
    assert p1.startswith("EMP-")


def test_pseudonym_different_inputs():
    """Different inputs yield different pseudonyms."""
    p1 = generate_pseudonym("Ahmet")
    p2 = generate_pseudonym("Mehmet")
    assert p1 != p2


def test_mask_value_static():
    """Static fields are replaced with a fixed mask."""
    lookup = {}
    assert mask_value("mobilePhone", "+905554443322", lookup) == "***MASKED***"
    assert mask_value("nationalId", "12345678901", lookup) == "***MASKED***"


def test_mask_value_email():
    """Email fields get a user-XXXX@masked.local format."""
    lookup = {}
    masked = mask_value("workEmail", "ahmet@company.com", lookup)
    assert masked.endswith("@masked.local")
    assert masked.startswith("user-")
    assert masked in lookup
    assert lookup[masked] == "Masked from workEmail"


def test_mask_value_name():
    """Names get EMP-XXXX format."""
    lookup = {}
    masked = mask_value("firstName", "Ahmet", lookup)
    assert masked.startswith("EMP-")
    assert masked in lookup
    assert lookup[masked] == "Masked from firstName"


@patch("os.environ.get", return_value="true")
def test_mask_value_amount_enabled(mock_env):
    """Financial amounts are bucketed when enabled."""
    lookup = {}
    assert mask_value("amount", 15250, lookup) == "15000-16000"
    assert mask_value("gross", 850, lookup) == "800-900"
    assert mask_value("totalAmount", "invalid", lookup) == "***MASKED***"


@patch("os.environ.get", return_value="false")
def test_mask_value_amount_disabled(mock_env):
    """Financial amounts are left alone when disabled."""
    lookup = {}
    assert mask_value("amount", 15250, lookup) == 15250


def test_mask_dict_recursive():
    """mask_dict walks nested structures."""
    lookup = {}
    data = {
        "id": "123",
        "department": "Engineering",
        "manager": {
            "firstName": "John",
            "lastName": "Doe",
            "workEmail": "john@example.com"
        },
        "tags": ["tech", "lead"]
    }
    
    masked = mask_dict(data, lookup)
    
    # Non-PII fields untouched
    assert masked["id"] == "123"
    assert masked["department"] == "Engineering"
    assert masked["tags"] == ["tech", "lead"]
    
    # PII fields masked
    manager = masked["manager"]
    assert manager["firstName"].startswith("EMP-")
    assert manager["lastName"].startswith("EMP-")
    assert manager["workEmail"].startswith("user-")
    assert manager["workEmail"].endswith("@masked.local")
    
    # Lookup populated
    assert manager["firstName"] in lookup
    assert manager["workEmail"] in lookup


def test_middleware_masks_json_content():
    """Middleware parses JSON, masks it, and rewrites the content."""
    import asyncio
    middleware = PIIMaskingMiddleware()
    ctx = MockMiddlewareContext()
    
    raw_data = {
        "items": [
            {"id": "1", "firstName": "Alice", "lastName": "Smith", "workEmail": "alice@co.com"},
            {"id": "2", "firstName": "Bob", "lastName": "Jones", "workEmail": "bob@co.com"}
        ],
        "totalCount": 2
    }
    
    mock_result = MockToolResult([TextContent(type="text", text=json.dumps(raw_data))])
    
    async def call_next_mock(context):
        return mock_result
        
    result = asyncio.run(middleware.on_call_tool(ctx, call_next_mock))
    
    new_text = result.content[0].text
    parsed = json.loads(new_text)
    
    assert "items" in parsed
    assert parsed["totalCount"] == 2
    
    item1 = parsed["items"][0]
    assert item1["id"] == "1"
    assert item1["firstName"].startswith("EMP-")
    assert item1["firstName"] != "Alice"
    assert item1["workEmail"].endswith("@masked.local")
    
    assert "_pii_lookup" in parsed
    assert item1["firstName"] in parsed["_pii_lookup"]


def test_middleware_ignores_non_json():
    """Middleware doesn't blow up on plain text that isn't JSON."""
    import asyncio
    middleware = PIIMaskingMiddleware()
    ctx = MockMiddlewareContext()
    
    mock_result = MockToolResult([TextContent(type="text", text="Just a regular string")])
    
    async def call_next_mock(context):
        return mock_result
        
    result = asyncio.run(middleware.on_call_tool(ctx, call_next_mock))
    
    assert result.content[0].text == "Just a regular string"


@patch("os.environ.get")
def test_custom_fields(mock_env):
    """Custom fields specified via env var are masked statically."""
    # Only return true for custom fields
    def mock_get(key, default=""):
        if key == "MCP_PII_MASK_FIELDS":
            return "customSecret, anotherField"
        return default
    
    mock_env.side_effect = mock_get

    lookup = {}
    assert mask_value("customSecret", "secret_value", lookup) == "***MASKED***"
    assert mask_value("anotherField", 123, lookup) == "***MASKED***"
    assert mask_value("firstName", "John", lookup).startswith("EMP-") # Regular PII still works


def test_middleware_static_mask_updates_content():
    """Middleware updates content even when only static fields (no lookup) are masked."""
    import asyncio
    middleware = PIIMaskingMiddleware()
    ctx = MockMiddlewareContext()

    raw_data = {"nationalId": "12345678901", "status": "active"}
    mock_result = MockToolResult([TextContent(type="text", text=json.dumps(raw_data))])

    async def call_next_mock(context):
        return mock_result

    result = asyncio.run(middleware.on_call_tool(ctx, call_next_mock))

    parsed = json.loads(result.content[0].text)
    assert parsed["nationalId"] == "***MASKED***"
    assert parsed["status"] == "active"
