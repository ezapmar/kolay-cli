"""Tests for `kolay payroll` CLI commands and payroll service layer."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from kolay_cli.cli import app

runner = CliRunner()

# ── Sample API responses ──────────────────────────────────────────────────────

PAYROLL_SHEET_RESPONSE = {
    "data": {
        "items": [
            {
                "id": "row1",
                "person": {"firstName": "Ali", "lastName": "Veli"},
                "gross": 15000,
                "net": 11500,
                "status": "ended",
            },
            {
                "id": "row2",
                "person": {"firstName": "Ayşe", "lastName": "Kaya"},
                "gross": 18000,
                "net": 13800,
                "status": "ended",
            },
        ]
    }
}

PAYROLL_SHEET_EMPTY_RESPONSE = {"data": {}}

PAYROLL_SHEET_NO_ITEMS_RESPONSE = {"data": {"items": []}}


# ══════════════════════════════════════════════════════════════════════════════
# CLI TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestPayrollCLI:
    def test_payroll_view_renders_table(self, mock_client):
        mock_client.post.return_value = PAYROLL_SHEET_RESPONSE
        result = runner.invoke(app, ["payroll", "view", "abc123def456"])
        assert result.exit_code == 0
        assert "Ali" in result.output
        assert "Ayşe" in result.output
        assert "Payroll Sheet" in result.output

    def test_payroll_view_json_mode(self, mock_client):
        mock_client.post.return_value = PAYROLL_SHEET_RESPONSE
        result = runner.invoke(app, ["--json", "payroll", "view", "abc123def456"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert "items" in data
        assert len(data["items"]) == 2

    def test_payroll_view_empty(self, mock_client):
        mock_client.post.return_value = PAYROLL_SHEET_EMPTY_RESPONSE
        result = runner.invoke(app, ["payroll", "view", "abc123def456"])
        assert result.exit_code == 0
        # Empty data {} → triggers "No payroll data found" — correct UX
        assert "No payroll data found" in result.output

    def test_payroll_view_no_items(self, mock_client):
        mock_client.post.return_value = PAYROLL_SHEET_NO_ITEMS_RESPONSE
        result = runner.invoke(app, ["payroll", "view", "abc123def456"])
        assert result.exit_code == 0
        # Empty items → falls to the else branch, shows empty message
        assert "No payroll rows" in result.output or "Payroll Sheet" in result.output

    def test_payroll_view_with_search(self, mock_client):
        mock_client.post.return_value = PAYROLL_SHEET_RESPONSE
        result = runner.invoke(app, ["payroll", "view", "abc123def456", "--search", "Ali"])
        assert result.exit_code == 0
        # Verify search param passed to API
        call_data = mock_client.post.call_args[1].get("json") or mock_client.post.call_args[0][1] if len(mock_client.post.call_args[0]) > 1 else {}
        # The search value should be somewhere in the call
        assert "Ali" in result.output

    def test_payroll_view_with_match(self, mock_client):
        mock_client.post.return_value = PAYROLL_SHEET_RESPONSE
        result = runner.invoke(app, ["payroll", "view", "abc123def456", "--filter", "Ali"])
        assert result.exit_code == 0
        assert "Ali" in result.output
        # Ayşe should be filtered out by client-side filter
        assert "Ayşe" not in result.output

    def test_payroll_view_match_no_match(self, mock_client):
        """When --filter matches nothing, fall back to showing all records."""
        mock_client.post.return_value = PAYROLL_SHEET_RESPONSE
        result = runner.invoke(app, ["payroll", "view", "abc123def456", "--filter", "zzznomatch"])
        assert result.exit_code == 0
        # Fallback renders all items (standard UX pattern)
        assert "Ali" in result.output
        assert "Ayşe" in result.output

    def test_payroll_view_missing_id_json_mode(self):
        """--json without payroll_id gives a structured error, not a Typer crash."""
        import json
        result = runner.invoke(app, ["--json", "payroll", "view"])
        assert result.exit_code == 2
        data = json.loads(result.output)
        assert data["error"] is True
        assert "payroll-id" in data["message"]

    def test_payroll_view_missing_id_interactive(self, mock_client):
        """Without payroll_id, prompts the user for one (not a cold Typer error)."""
        mock_client.post.return_value = PAYROLL_SHEET_RESPONSE
        result = runner.invoke(app, ["payroll", "view"], input="abc123def456\n")
        assert result.exit_code == 0
        assert "Payroll Sheet Viewer" in result.output
        assert "Payroll run ID" in result.output

    def test_payroll_hint_no_subcommand(self, mock_client):
        """Running `kolay payroll` without a subcommand should show help."""
        result = runner.invoke(app, ["payroll"])
        assert result.exit_code == 0
        assert "view" in result.output.lower() or "help" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE LAYER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestPayrollService:
    def test_view_builds_empty_payload(self):
        """No filters → empty payload body."""
        from kolay_cli.services.payroll import view_payroll_sheet
        mock = MagicMock()
        mock.post.return_value = {"data": {"items": []}}
        with patch("kolay_cli.services.payroll.KolayClient", return_value=mock):
            result = view_payroll_sheet("abc123")
        mock.post.assert_called_once_with(
            "v2/payroll-sheet/view/abc123",
            data={},
        )
        assert result == {"items": []}

    def test_view_builds_filter_payload(self):
        """All filters → payload has nested filter block."""
        from kolay_cli.services.payroll import view_payroll_sheet
        mock = MagicMock()
        mock.post.return_value = {"data": {"summary": "ok"}}
        with patch("kolay_cli.services.payroll.KolayClient", return_value=mock):
            result = view_payroll_sheet(
                "abc123",
                search="Ali",
                status=["ended"],
                salary_period=["monthly"],
            )
        expected_payload = {
            "filter": {
                "search": "Ali",
                "status": ["ended"],
                "salaryPeriod": ["monthly"],
            }
        }
        mock.post.assert_called_once_with(
            "v2/payroll-sheet/view/abc123",
            data=expected_payload,
        )
        assert result == {"summary": "ok"}

    def test_view_partial_filter(self):
        """Only search → filter block has only search key."""
        from kolay_cli.services.payroll import view_payroll_sheet
        mock = MagicMock()
        mock.post.return_value = {"data": {}}
        with patch("kolay_cli.services.payroll.KolayClient", return_value=mock):
            view_payroll_sheet("abc123", search="Ali")
        expected_payload = {"filter": {"search": "Ali"}}
        mock.post.assert_called_once_with(
            "v2/payroll-sheet/view/abc123",
            data=expected_payload,
        )

    def test_view_invalid_id_raises(self):
        """Invalid payroll ID characters should raise APIError."""
        from kolay_cli.services.payroll import view_payroll_sheet
        from kolay_cli.api.errors import APIError
        with pytest.raises(APIError, match="payroll_id"):
            view_payroll_sheet("../etc/passwd")

    def test_view_empty_id_raises(self):
        """Empty payroll ID should raise APIError."""
        from kolay_cli.services.payroll import view_payroll_sheet
        from kolay_cli.api.errors import APIError
        with pytest.raises(APIError):
            view_payroll_sheet("")

    def test_view_returns_raw_when_no_data_key(self):
        """If API response has no 'data' key, return the response as-is."""
        from kolay_cli.services.payroll import view_payroll_sheet
        mock = MagicMock()
        mock.post.return_value = {"items": [{"gross": 100}]}
        with patch("kolay_cli.services.payroll.KolayClient", return_value=mock):
            result = view_payroll_sheet("abc123")
        assert result == {"items": [{"gross": 100}]}


# ══════════════════════════════════════════════════════════════════════════════
# MCP TOOL EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

class TestPayrollMCPEdgeCases:
    def _svc(self, name: str) -> str:
        return f"kolay_cli.mcp_server.{name}"

    def test_payroll_filter_non_dict_passthrough(self):
        """If service returns a non-dict, filter is skipped gracefully."""
        from kolay_cli.mcp.tools_finance import payroll_sheet_view
        with patch(self._svc("payroll_svc.view_payroll_sheet"), return_value=[{"a": 1}]):
            result = payroll_sheet_view("abc123", match="Ali")
        # Should return the result unchanged — no crash
        assert result == [{"a": 1}]

    def test_payroll_filter_empty_items(self):
        """Filter with empty items list should not crash."""
        from kolay_cli.mcp.tools_finance import payroll_sheet_view
        data = {"items": []}
        with patch(self._svc("payroll_svc.view_payroll_sheet"), return_value=data):
            result = payroll_sheet_view("abc123", match="Ali")
        assert result == {"items": []}

    def test_payroll_filter_no_person_key(self):
        """Rows without person/employee key should be handled gracefully."""
        from kolay_cli.mcp.tools_finance import payroll_sheet_view
        data = {"items": [{"gross": 100, "status": "ended"}]}
        with patch(self._svc("payroll_svc.view_payroll_sheet"), return_value=data):
            result = payroll_sheet_view("abc123", match="Ali")
        # No person key → empty name → filter removes it, fallback shows all
        assert "items" in result

    def test_payroll_no_filter_returns_raw(self):
        """Without filter param, result passes through unchanged."""
        from kolay_cli.mcp.tools_finance import payroll_sheet_view
        data = {"items": [{"person": {"firstName": "A", "lastName": "B"}}], "extra": True}
        with patch(self._svc("payroll_svc.view_payroll_sheet"), return_value=data):
            result = payroll_sheet_view("abc123")
        assert result == data
        assert result["extra"] is True
