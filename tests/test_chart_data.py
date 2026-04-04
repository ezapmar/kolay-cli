"""Tests for chart-ready visualization data aggregation (chart_data module)."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from datetime import date


# ---------------------------------------------------------------------------
# Fixtures / shared mock data
# ---------------------------------------------------------------------------

MOCK_LEAVES = [
    {
        "id": "leave-1",
        "person": {"id": "p1", "firstName": "Ali", "lastName": "Yilmaz",
                    "department": "Engineering"},
        "leaveType": {"name": "Annual"},
        "startDate": "2026-03-01 09:00:00",
        "endDate": "2026-03-05 18:00:00",
        "dayCount": 5,
        "status": "approved",
    },
    {
        "id": "leave-2",
        "person": {"id": "p2", "firstName": "Ayse", "lastName": "Demir",
                    "department": "HR"},
        "leaveType": {"name": "Sick"},
        "startDate": "2026-03-10 09:00:00",
        "endDate": "2026-03-12 18:00:00",
        "dayCount": 3,
        "status": "approved",
    },
    {
        "id": "leave-3",
        "person": {"id": "p3", "firstName": "Mehmet", "lastName": "Kaya",
                    "department": "Engineering"},
        "leaveType": {"name": "Annual"},
        "startDate": "2026-04-01 09:00:00",
        "endDate": "2026-04-02 18:00:00",
        "dayCount": 2,
        "status": "approved",
    },
]

MOCK_UNIT_TREE = [
    {
        "name": "Company",
        "items": [],
        "children": [
            {
                "name": "Engineering",
                "items": [
                    {"personId": "p1", "name": "Ali Yilmaz"},
                    {"personId": "p3", "name": "Mehmet Kaya"},
                    {"personId": "p4", "name": "Can Ozturk"},
                ],
                "children": [],
            },
            {
                "name": "HR",
                "items": [
                    {"personId": "p2", "name": "Ayse Demir"},
                ],
                "children": [],
            },
        ],
    },
]

MOCK_PEOPLE_ACTIVE = {
    "items": [
        {"id": "p1", "firstName": "Ali", "lastName": "Yilmaz",
         "employmentStartDate": "2025-06-01", "department": "Engineering"},
        {"id": "p2", "firstName": "Ayse", "lastName": "Demir",
         "employmentStartDate": "2024-01-15", "department": "HR"},
        {"id": "p3", "firstName": "Mehmet", "lastName": "Kaya",
         "employmentStartDate": "2026-01-10", "department": "Engineering"},
    ],
    "totalCount": 3,
    "page": 1,
}

MOCK_PEOPLE_PASSIVE = {
    "items": [
        {"id": "p5", "firstName": "Zeynep", "lastName": "Aksoy",
         "employmentStartDate": "2023-03-01",
         "terminationDate": "2025-11-15", "department": "Sales"},
    ],
    "totalCount": 1,
    "page": 1,
}

MOCK_TIMELOGS = {
    "items": [
        {
            "id": "tl1",
            "person": {"id": "p1", "firstName": "Ali", "lastName": "Yilmaz",
                        "department": "Engineering"},
            "startDate": "2026-03-01 18:00:00",
            "endDate": "2026-03-01 21:00:00",
            "type": "overtime",
        },
        {
            "id": "tl2",
            "person": {"id": "p2", "firstName": "Ayse", "lastName": "Demir",
                        "department": "HR"},
            "startDate": "2026-03-05 18:00:00",
            "endDate": "2026-03-05 19:30:00",
            "type": "overtime",
        },
    ],
    "totalCount": 2,
    "page": 1,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLeaveUsageByDepartment:
    @patch("kolay_cli.services.chart_data.leave_svc.list_leaves")
    def test_basic_aggregation(self, mock_leaves):
        from kolay_cli.services.chart_data import leave_usage_by_department

        mock_leaves.return_value = MOCK_LEAVES
        result = leave_usage_by_department(start="2026-01-01", end="2026-12-31")

        assert result["chart_type"] == "pie"
        assert "labels" in result
        assert "datasets" in result
        assert len(result["datasets"]) == 1
        assert result["total_days"] == 10  # 5 + 3 + 2
        assert result["total_records"] == 3
        assert "Engineering" in result["labels"]
        assert "HR" in result["labels"]
        # Engineering should have more days (5 + 2 = 7)
        eng_idx = result["labels"].index("Engineering")
        assert result["datasets"][0]["data"][eng_idx] == 7
        assert len(result["reasoning_chain"]) > 0

    @patch("kolay_cli.services.chart_data.leave_svc.list_leaves")
    def test_empty_leaves(self, mock_leaves):
        from kolay_cli.services.chart_data import leave_usage_by_department

        mock_leaves.return_value = []
        result = leave_usage_by_department()

        assert result["chart_type"] == "pie"
        assert result["labels"] == []
        assert result["total_days"] == 0


class TestHeadcountByDepartment:
    @patch("kolay_cli.services.chart_data.unit_svc.unit_tree")
    def test_basic_count(self, mock_tree):
        from kolay_cli.services.chart_data import headcount_by_department

        mock_tree.return_value = MOCK_UNIT_TREE
        result = headcount_by_department()

        assert result["chart_type"] == "bar"
        assert "treemap" in result["chart_type_alternatives"]
        assert result["total_employees"] == 4  # 3 + 1
        assert result["labels"][0] == "Engineering"  # largest first
        assert result["datasets"][0]["data"][0] == 3

    @patch("kolay_cli.services.chart_data.unit_svc.unit_tree")
    def test_empty_units(self, mock_tree):
        from kolay_cli.services.chart_data import headcount_by_department

        mock_tree.return_value = [{"name": "Empty Co", "items": [], "children": []}]
        result = headcount_by_department()

        assert result["total_employees"] == 0
        assert result["labels"] == []


class TestAttendanceHeatmap:
    @patch("kolay_cli.services.chart_data.leave_svc.list_leaves")
    def test_basic_heatmap(self, mock_leaves):
        from kolay_cli.services.chart_data import attendance_heatmap

        mock_leaves.return_value = MOCK_LEAVES
        result = attendance_heatmap(year="2026")

        assert result["chart_type"] == "calendar_heatmap"
        assert result["library"] == "echarts"
        assert result["year"] == "2026"
        assert isinstance(result["data"], list)
        # Should have entries for dates in March and April
        dates = [d[0] for d in result["data"]]
        assert "2026-03-01" in dates
        assert result["max_value"] > 0
        assert result["total_absence_days"] > 0

    @patch("kolay_cli.services.chart_data.leave_svc.list_leaves")
    def test_empty_year(self, mock_leaves):
        from kolay_cli.services.chart_data import attendance_heatmap

        mock_leaves.return_value = []
        result = attendance_heatmap(year="2026")

        assert result["data"] == []
        assert result["max_value"] == 0


class TestHeadcountTrend:
    @patch("kolay_cli.services.chart_data.person_svc.list_people")
    def test_basic_trend(self, mock_people):
        from kolay_cli.services.chart_data import headcount_trend

        def side_effect(status="active", limit=200):
            if status == "active":
                return MOCK_PEOPLE_ACTIVE
            return MOCK_PEOPLE_PASSIVE

        mock_people.side_effect = side_effect
        result = headcount_trend(months=12)

        assert result["chart_type"] == "line"
        assert len(result["datasets"]) == 2
        assert result["datasets"][0]["label"] == "Joined"
        assert result["datasets"][1]["label"] == "Left"
        assert len(result["labels"]) > 0
        assert result["period_months"] == 12
        assert "net_change" in result


class TestLeaveTypeBreakdown:
    @patch("kolay_cli.services.chart_data.leave_svc.list_leaves")
    def test_basic_breakdown(self, mock_leaves):
        from kolay_cli.services.chart_data import leave_type_breakdown

        mock_leaves.return_value = MOCK_LEAVES
        result = leave_type_breakdown()

        assert result["chart_type"] == "doughnut"
        assert "Annual" in result["labels"]
        assert "Sick" in result["labels"]
        assert result["total_days"] == 10
        assert result["total_requests"] == 3
        # Annual: 2 requests (5 + 2 = 7 days), Sick: 1 request (3 days)
        annual_idx = result["labels"].index("Annual")
        assert result["datasets"][0]["data"][annual_idx] == 7
        assert result["request_counts"][annual_idx] == 2


class TestOvertimeByDepartment:
    @patch("kolay_cli.services.chart_data.timelog_svc.list_timelogs")
    def test_basic_overtime(self, mock_timelogs):
        from kolay_cli.services.chart_data import overtime_by_department

        mock_timelogs.return_value = MOCK_TIMELOGS
        result = overtime_by_department()

        assert result["chart_type"] == "bar"
        assert "Engineering" in result["labels"]
        assert "HR" in result["labels"]
        assert result["total_hours"] == 4.5  # 3.0 + 1.5
        assert result["total_records"] == 2

    @patch("kolay_cli.services.chart_data.timelog_svc.list_timelogs")
    def test_empty_timelogs(self, mock_timelogs):
        from kolay_cli.services.chart_data import overtime_by_department

        mock_timelogs.return_value = {"items": [], "totalCount": 0, "page": 1}
        result = overtime_by_department()

        assert result["total_hours"] == 0
        assert result["labels"] == []


class TestChartDataEnvelope:
    """Verify all chart functions return the expected envelope structure."""

    @patch("kolay_cli.services.chart_data.leave_svc.list_leaves")
    @patch("kolay_cli.services.chart_data.unit_svc.unit_tree")
    @patch("kolay_cli.services.chart_data.person_svc.list_people")
    @patch("kolay_cli.services.chart_data.timelog_svc.list_timelogs")
    def test_all_charts_have_required_fields(
        self, mock_timelogs, mock_people, mock_tree, mock_leaves
    ):
        from kolay_cli.services import chart_data

        mock_leaves.return_value = MOCK_LEAVES
        mock_tree.return_value = MOCK_UNIT_TREE
        mock_people.return_value = MOCK_PEOPLE_ACTIVE
        mock_timelogs.return_value = MOCK_TIMELOGS

        charts = [
            chart_data.leave_usage_by_department(),
            chart_data.headcount_by_department(),
            chart_data.leave_type_breakdown(),
            chart_data.overtime_by_department(),
        ]

        for chart in charts:
            assert "chart_type" in chart, f"Missing chart_type in {chart.get('title')}"
            assert "title" in chart, f"Missing title"
            assert "labels" in chart, f"Missing labels in {chart.get('title')}"
            assert "datasets" in chart, f"Missing datasets in {chart.get('title')}"
            assert "reasoning_chain" in chart, f"Missing reasoning_chain in {chart.get('title')}"
            # datasets should be a list of dicts with 'label' and 'data'
            for ds in chart["datasets"]:
                assert "label" in ds
                assert "data" in ds
                assert isinstance(ds["data"], list)

    @patch("kolay_cli.services.chart_data.leave_svc.list_leaves")
    def test_heatmap_has_required_fields(self, mock_leaves):
        from kolay_cli.services.chart_data import attendance_heatmap

        mock_leaves.return_value = MOCK_LEAVES
        result = attendance_heatmap(year="2026")

        assert result["chart_type"] == "calendar_heatmap"
        assert result["library"] == "echarts"
        assert "year" in result
        assert "data" in result
        assert "max_value" in result
        assert "reasoning_chain" in result
