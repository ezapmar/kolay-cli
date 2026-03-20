from fastmcp.tools import Tool
from typing import Any
from fastmcp.server.context import Context
from fastmcp.dependencies import CurrentContext
from ..security import require_auth
from ..services import person as person_svc
from ..services import leave as leave_svc
from ..services import timelog as timelog_svc
from ..services import training as training_svc
from ..services import transaction as transaction_svc
from ..services import calendar as calendar_svc
from ..services import unit as unit_svc
from ..services import approval as approval_svc
from ..services import hr_analytics as hr_analytics_svc
from ..services import payroll as payroll_svc
from ..services import wellness as wellness_svc
from ..ui.search import filter_items_silent
from ..mcp_progress import sync_progress_bridge
import json


@require_auth
def team_availability_analysis(
    unit_name: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """[READ] Multi-step team availability and operational risk assessment.
    Internally queries the Leave API and Unit API, then computes:
    peak concurrent absences, availability %, and a risk classification
    (normal / low / medium / high / critical).

    Returns structured JSON including a 'reasoning_chain' that documents
    every decision step — suitable for any downstream LLM or dashboard.

    unit_name: Full or partial name of the organisational unit (e.g. 'Engineering').
    start_date / end_date: Date range in YYYY-MM-DD format."""
    return hr_analytics_svc.team_availability_analysis(unit_name, start_date, end_date)


@require_auth
def turnover_risk_scan(
    search: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """[READ] Scan active employees for turnover and burnout risk signals.
    Internally fetches the employee list then queries leave balances for each
    person. Risk signals include: high unused annual leave (burnout),
    new-hire flight-risk window, and disengagement (long tenure, zero leave taken).

    Returns employees ranked by risk_score with per-person signal explanations
    and an organisation-wide risk_distribution summary.

    search: Optional department or name fragment to narrow the scan.
    limit: Max employees to scan (default 50; raise for org-wide scans)."""
    return hr_analytics_svc.turnover_risk_scan(search=search, limit=limit)


@require_auth
def payroll_anomaly_detect(months_back: int = 3) -> dict[str, Any]:
    """[READ] Detect anomalies in recent payroll and transaction data.
    Runs two checks:
      1. Duplicate detection — same person, type, and date appearing more than once.
      2. Statistical outliers — amounts exceeding mean + 2σ for their transaction type.

    Returns a ranked anomaly list (high severity first) with per-item explanations
    and a 'reasoning_chain' showing every analytical step.

    months_back: How many months of history to scan (default 3)."""
    return hr_analytics_svc.payroll_anomaly_detect(months_back=months_back)


def register(mcp):
    mcp.add_tool(Tool.from_function(team_availability_analysis, annotations={"readOnlyHint": True, "openWorldHint": True}))
    mcp.add_tool(Tool.from_function(turnover_risk_scan, annotations={"readOnlyHint": True, "openWorldHint": True}))
    mcp.add_tool(Tool.from_function(payroll_anomaly_detect, annotations={"readOnlyHint": True, "openWorldHint": True}))
