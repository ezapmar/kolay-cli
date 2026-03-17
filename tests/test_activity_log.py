"""Tests for structured MCP activity logger."""
from __future__ import annotations

import json
import logging
from io import StringIO

import pytest

from kolay_cli.activity_log import _redact_args, log_tool_call


class TestRedactArgs:
    def test_short_values_pass_through(self):
        args = {"status": "active", "page": 1}
        assert _redact_args(args) == args

    def test_long_string_redacted(self):
        long_val = "x" * 100
        result = _redact_args({"description": long_val})
        assert result["description"] == "[redacted:100 chars]"

    def test_nested_dict_redacted(self):
        result = _redact_args({"custom": {"bio": "y" * 200}})
        assert result["custom"]["bio"] == "[redacted:200 chars]"

    def test_non_string_values_preserved(self):
        args = {"limit": 20, "active": True, "tags": ["a", "b"]}
        assert _redact_args(args) == args

    def test_empty_dict(self):
        assert _redact_args({}) == {}


@pytest.fixture()
def capture_activity_log():
    """Capture activity logger output via a StringIO handler."""
    logger = logging.getLogger("kolay.activity")
    buf = StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    yield buf
    logger.removeHandler(handler)


class TestLogToolCall:
    def test_log_outputs_json(self, capture_activity_log):
        log_tool_call(
            token_key="tok_…test1234",
            tool_name="person_list",
            args={"status": "active", "limit": 20},
            duration_s=0.142,
            success=True,
        )

        output = capture_activity_log.getvalue().strip()
        assert output, "Expected log output but got nothing"
        record = json.loads(output)
        assert record["event"] == "mcp.tool_call"
        assert record["token_key"] == "tok_…test1234"
        assert record["tool"] == "person_list"
        assert record["success"] is True
        assert record["error"] is None
        assert record["duration_ms"] == 142.0
        assert record["args_summary"] == {"status": "active", "limit": 20}
        assert "ts" in record

    def test_error_logging(self, capture_activity_log):
        log_tool_call(
            token_key="tok_…err12345",
            tool_name="person_terminate",
            args={"person_id": "abc"},
            duration_s=0.05,
            success=False,
            error="APIError: 404 Not Found",
        )

        record = json.loads(capture_activity_log.getvalue().strip())
        assert record["success"] is False
        assert record["error"] == "APIError: 404 Not Found"
        assert record["tool"] == "person_terminate"

    def test_args_redaction_in_log(self, capture_activity_log):
        log_tool_call(
            token_key="tok_…redact12",
            tool_name="training_create",
            args={"name": "Python", "description": "A" * 200},
            duration_s=0.1,
        )

        record = json.loads(capture_activity_log.getvalue().strip())
        assert record["args_summary"]["name"] == "Python"
        assert record["args_summary"]["description"] == "[redacted:200 chars]"

    def test_empty_args(self, capture_activity_log):
        log_tool_call(
            token_key="tok_…empty123",
            tool_name="validate_connection",
            args={},
            duration_s=0.01,
        )

        record = json.loads(capture_activity_log.getvalue().strip())
        assert record["args_summary"] == {}
