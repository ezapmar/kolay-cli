"""Chart-ready visualization MCP tools.

These tools return pre-aggregated, chart-shaped payloads that the LLM
drops directly into Chart.js or ECharts HTML templates.  The LLM does
NOT need to compute aggregations -- it just wires the data into a
visualization artifact.

Tool naming convention: chart_* prefix signals to the LLM that these
return visualization-ready data, not raw records.
"""
from .adapter import Tool
from typing import Any
from ..security import require_auth
from ..services import chart_data
from ..proxy.semantic_cache import semantic_cached


@require_auth
@semantic_cached(ttl=900)
def chart_leave_by_department(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """[READ] Chart-ready: leave day-counts aggregated by department.

    Returns pre-shaped data for a pie, bar, or doughnut chart.
    The 'labels' and 'datasets' fields map directly to Chart.js config.

    Suggested visualization: pie chart or horizontal bar chart.

    start_date: Period start (YYYY-MM-DD). Defaults to Jan 1 of current year.
    end_date: Period end (YYYY-MM-DD). Defaults to Dec 31 of current year."""
    return chart_data.leave_usage_by_department(start=start_date, end=end_date)


@require_auth
@semantic_cached(ttl=900)
def chart_headcount_by_department() -> dict[str, Any]:
    """[READ] Chart-ready: active employee count per organisational unit.

    Returns pre-shaped data for a bar chart or treemap.
    For treemap (ECharts), use labels as names and datasets[0].data as values.

    Suggested visualization: horizontal bar chart or ECharts treemap."""
    return chart_data.headcount_by_department()


@require_auth
@semantic_cached(ttl=900)
def chart_absence_heatmap(
    year: str | None = None,
) -> dict[str, Any]:
    """[READ] Chart-ready: daily absence counts for a calendar year heatmap.

    Returns data shaped for an ECharts calendar heatmap:
    'data' contains [[date_string, count], ...] pairs.

    IMPORTANT: Render this with ECharts (not Chart.js). Use the echarts
    calendar component with visualMap for color intensity.

    year: Target year (YYYY). Defaults to current year."""
    return chart_data.attendance_heatmap(year=year)


@require_auth
@semantic_cached(ttl=900)
def chart_headcount_trend(
    months: int = 12,
) -> dict[str, Any]:
    """[READ] Chart-ready: monthly joiners vs leavers trend line.

    Returns two datasets ('Joined' and 'Left') with matching monthly labels.
    The 'net_change' field shows total headcount growth/shrinkage.

    Suggested visualization: dual-line chart or grouped bar chart.

    months: How many months of history to show (default 12)."""
    return chart_data.headcount_trend(months=months)


@require_auth
@semantic_cached(ttl=900)
def chart_leave_type_breakdown(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """[READ] Chart-ready: leave days grouped by leave type.

    Returns pre-shaped data for a doughnut or pie chart showing the
    distribution of annual, sick, maternity, and other leave types.

    start_date: Period start (YYYY-MM-DD). Defaults to Jan 1 of current year.
    end_date: Period end (YYYY-MM-DD). Defaults to Dec 31 of current year."""
    return chart_data.leave_type_breakdown(start=start_date, end=end_date)


@require_auth
@semantic_cached(ttl=900)
def chart_overtime_by_department(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """[READ] Chart-ready: overtime hours aggregated by department.

    Returns pre-shaped data for a bar chart showing overtime distribution.

    start_date: Period start (YYYY-MM-DD). Defaults to Jan 1 of current year.
    end_date: Period end (YYYY-MM-DD). Defaults to Dec 31 of current year."""
    return chart_data.overtime_by_department(start=start_date, end=end_date)


def register(mcp):
    """Register all chart-ready visualization tools."""
    for fn in [
        chart_leave_by_department,
        chart_headcount_by_department,
        chart_absence_heatmap,
        chart_headcount_trend,
        chart_leave_type_breakdown,
        chart_overtime_by_department,
    ]:
        mcp.add_tool(Tool.from_function(
            fn,
            annotations={"readOnlyHint": True, "openWorldHint": True},
            timeout=60.0,
            tags={"read", "analytics", "chart"},
        ))
