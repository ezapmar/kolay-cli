"""Tests for payload padding middleware."""
from __future__ import annotations

import asyncio
import json

from kolay_cli.payload_padder import PayloadPaddingMiddleware, _get_pad_target
from mcp.types import TextContent


class MockToolResult:
    def __init__(self, content):
        self.content = content

class MockCtx:
    pass


def test_get_pad_target_default():
    """Default target is 64 KB."""
    target = _get_pad_target()
    assert target == 64 * 1024


def test_padding_applied_to_small_json():
    """Small JSON responses are padded to the target size."""
    middleware = PayloadPaddingMiddleware()
    ctx = MockCtx()

    small_data = {"id": "1", "name": "test"}
    mock_result = MockToolResult([TextContent(type="text", text=json.dumps(small_data))])

    async def call_next(context):
        return mock_result

    result = asyncio.run(middleware.on_call_tool(ctx, call_next))

    padded_text = result.content[0].text
    parsed = json.loads(padded_text)

    assert "_pad" in parsed
    assert parsed["id"] == "1"
    assert len(padded_text.encode("utf-8")) >= _get_pad_target()


def test_large_response_not_truncated():
    """Responses already larger than target are left untouched."""
    middleware = PayloadPaddingMiddleware()
    ctx = MockCtx()

    # Create a response larger than 64 KB
    big_data = {"data": "x" * (70 * 1024)}
    original_text = json.dumps(big_data)
    mock_result = MockToolResult([TextContent(type="text", text=original_text)])

    async def call_next(context):
        return mock_result

    result = asyncio.run(middleware.on_call_tool(ctx, call_next))
    assert result.content[0].text == original_text
    assert "_pad" not in json.loads(result.content[0].text)


def test_non_json_padded_with_whitespace():
    """Non-JSON text is padded with trailing whitespace."""
    middleware = PayloadPaddingMiddleware()
    ctx = MockCtx()

    mock_result = MockToolResult([TextContent(type="text", text="hello world")])

    async def call_next(context):
        return mock_result

    result = asyncio.run(middleware.on_call_tool(ctx, call_next))
    padded = result.content[0].text
    assert padded.startswith("hello world")
    assert len(padded.encode("utf-8")) >= _get_pad_target()


def test_empty_result_passthrough():
    """Empty results pass through without error."""
    middleware = PayloadPaddingMiddleware()
    ctx = MockCtx()

    mock_result = MockToolResult([])

    async def call_next(context):
        return mock_result

    result = asyncio.run(middleware.on_call_tool(ctx, call_next))
    assert result.content == []
