"""
tests/test_mcp_resources.py — Tests for MCP resource endpoints.

Covers the four @mcp.resource functions: reason_codes, turkish_holidays,
leave_types, and org_chart.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest


class TestReasonCodesResource:
    def test_returns_valid_json(self):
        from kolay_cli.mcp_server import reason_codes
        result = reason_codes()
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_contains_known_codes(self):
        from kolay_cli.mcp_server import reason_codes
        data = json.loads(reason_codes())
        assert "03" in data  # voluntary resignation
        assert "11" in data  # retirement
        assert "30" in data  # other

    def test_values_are_strings(self):
        from kolay_cli.mcp_server import reason_codes
        data = json.loads(reason_codes())
        for code, desc in data.items():
            assert isinstance(code, str)
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestTurkishHolidaysResource:
    def test_returns_valid_json_for_2026(self):
        from kolay_cli.mcp_server import turkish_holidays
        result = turkish_holidays("2026")
        data = json.loads(result)
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_contains_known_fixed_holidays(self):
        from kolay_cli.mcp_server import turkish_holidays
        data = json.loads(turkish_holidays("2026"))
        # National Sovereignty Day is always April 23
        assert "2026-04-23" in data
        # Republic Day is always October 29
        assert "2026-10-29" in data

    def test_contains_religious_holidays_2026(self):
        from kolay_cli.mcp_server import turkish_holidays
        data = json.loads(turkish_holidays("2026"))
        # Ramazan Bayrami 2026 starts March 20
        assert "2026-03-20" in data

    def test_dates_are_iso_format(self):
        from kolay_cli.mcp_server import turkish_holidays
        data = json.loads(turkish_holidays("2025"))
        for date_str in data.keys():
            assert len(date_str) == 10  # YYYY-MM-DD
            assert date_str[4] == "-"
            assert date_str[7] == "-"


class TestLeaveTypesResource:
    def test_returns_formatted_leave_balances(self):
        from kolay_cli.mcp.tools_leaves import leave_types

        mock_balances = [
            {
                "leaveTypeId": "lt1",
                "leaveType": {"name": "Annual Leave"},
                "total": 14,
                "used": 3,
                "unused": 11,
                "isPaid": True,
            },
            {
                "leaveTypeId": "lt2",
                "leaveType": {"name": "Sick Leave"},
                "total": 10,
                "used": 1,
                "unused": 9,
                "isPaid": True,
            },
        ]
        with patch("kolay_cli.services.person.leave_status", return_value=mock_balances):
            result = leave_types("person123")
        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["name"] == "Annual Leave"
        assert data[0]["leave_type_id"] == "lt1"
        assert data[0]["unused"] == 11
        assert data[1]["name"] == "Sick Leave"

    def test_handles_empty_balances(self):
        from kolay_cli.mcp.tools_leaves import leave_types

        with patch("kolay_cli.services.person.leave_status", return_value=[]):
            result = leave_types("person123")
        data = json.loads(result)
        assert data == []

    def test_handles_missing_leave_type_name(self):
        from kolay_cli.mcp.tools_leaves import leave_types

        mock_balances = [{"leaveTypeId": "lt1", "total": 5, "used": 0, "unused": 5}]
        with patch("kolay_cli.services.person.leave_status", return_value=mock_balances):
            result = leave_types("person123")
        data = json.loads(result)
        assert data[0]["name"] == "Unknown"


class TestOrgChartResource:
    def test_returns_json_tree(self):
        from kolay_cli.mcp_server import org_chart

        mock_tree = [
            {
                "id": "u1",
                "name": "Engineering",
                "children": [
                    {"id": "u2", "name": "Backend", "children": [], "items": []}
                ],
                "items": [{"id": "p1", "name": "Ali Veli"}],
            }
        ]
        with patch("kolay_cli.services.unit.unit_tree", return_value=mock_tree):
            result = org_chart()
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["name"] == "Engineering"
        assert data[0]["children"][0]["name"] == "Backend"

    def test_handles_empty_tree(self):
        from kolay_cli.mcp_server import org_chart

        with patch("kolay_cli.services.unit.unit_tree", return_value=[]):
            result = org_chart()
        data = json.loads(result)
        assert data == []
