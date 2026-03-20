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


def employee_snapshot(person_query: str) -> str:
    """Generate HR snapshot and leave balance report for an employee."""
    return f"""Act as an HR Manager.
Use the `person_list` tool to find the exact ID for the employee matching "{person_query}".
Then, use `person_view` and `person_leave_status` to gather their data.
Output a clean Markdown report with:
1) ID Card (Name, Department, Title)
2) Tenure (calculated precisely from employmentStartDate)
3) A list of leaves where 'unused' > 0 (specifically highlighting Annual Leave)."""


def burnout_analyzer(department_name: str) -> str:
    """Analyze a department for burnout risk based on unused annual leave."""
    return f"""Act as an Employee Engagement Specialist.
Use the `person_list` tool (with an empty search or a specific one) to find all employees working in the `{department_name}` department.
Use the `person_leave_status` tool for each of these employees to check their Annual Leave balances (where `primary` is true).
Output a report highlighting employees with severe burnout risk (unused Annual Leave > 20 days).
Draft a professional email to their department manager suggesting they encourage these specific employees to take time off."""


def onboarding_plan(person_query: str) -> str:
    """Draft onboarding kit for a new hire."""
    return f"""Act as an Onboarding Specialist.
First, use the `person_list` tool with search="{person_query}" to find the employee. If multiple results are returned, pick the closest match by name.
Then use `person_view` with their ID to retrieve the exact Name, Department, and Title for the new hire.
Based on their profile and role, output 3 things:
1) A warm, energetic welcome email draft to be sent to the whole company.
2) A precise guessed IT Setup and Hardware checklist tailored to their specific Title and Department.
3) A first-week 30-minute introductory meeting schedule draft mapping out key department roles they should meet."""


def offboarding_plan(person_query: str) -> str:
    """Draft offboarding action plan for a departing employee."""
    return f"""Act as an HR Operations Specialist.
First, use the `person_list` tool with search="{person_query}" to find the employee. If multiple results are returned, pick the closest match by name.
Then use `person_view` and `person_leave_status` with their ID to retrieve the full profile and leave balances for the departing employee.
Review their 'unused' Annual Leave balance specifically.
Output an Offboarding Action Plan including:
1) The exact number of unused Annual Leave days that remain to be paid out.
2) A role-specific knowledge handover checklist based on their exact Title.
3) 5 strategic Exit Interview questions tailored specifically to their Department so they feel heard."""


def bulk_update_assistant(target_field: str, old_value: str, new_value: str) -> str:
    """Safe, human-in-the-loop bulk data cleanup across employees."""
    return f"""Act as an HR Data Specialist performing a controlled bulk data cleanup.
Follow these steps EXACTLY in order — do not skip or reorder them.

**Step 1 — Discovery:**
Call `person_list` with limit=200 and status='active' to retrieve all active employees.
If totalCount exceeds 200, paginate until you have fetched every record.

**Step 2 — Analysis:**
Scan every employee. Identify those whose `{target_field}` field matches or contains "{old_value}" (case-insensitive).
Build an internal list of matches.

**Step 3 — MANDATORY CONFIRMATION — DO NOT SKIP:**
STOP. Do NOT call any update tools yet.
Present this Markdown table to the user:

| # | Full Name | Current `{target_field}` | Will change to |
|---|-----------|--------------------------|----------------|
(one row per matched employee)

Then ask EXACTLY this question:
"Do you confirm updating `{target_field}` for these **N** employees from \\"{old_value}\\" \\"{new_value}\\"? (Yes / No)"

**Step 4 — Execute (only on explicit "Yes"):**
• If the user responds with "Yes": loop through each matched employee and call `person_update_fields` with their ID and {{"{target_field}": "{new_value}"}}.
  Confirm each update as it completes (e.g. "Updated Ahmet Yılmaz").
• If the user responds with anything other than "Yes": abort immediately and state "Operation cancelled. No changes were made."

**Step 5 — Final Summary:**
Present a concise summary: total scanned, total updated (or 0 if cancelled), any errors."""


def hr_capabilities() -> str:
    """Guided prompt explaining exactly what the Kolay HR AI can do for the user."""
    return """Act as a helpful HR Assistant. 
List the top things you can do for the user regarding their Kolay IK data. 
Categorize the capabilities (e.g., Time Off & Leaves, Work Hours & Timelogs, Team Directory, Training, Expenses).
Keep it very brief, punchy, and use emojis. Offer to help them with one of these right now."""


def team_risk_brief(unit_name: str, start_date: str, end_date: str) -> str:
    """Operational risk brief for a team covering a specific date range."""
    return f"""Act as an HR Operations Analyst.
Run `team_availability_analysis` with unit_name="{unit_name}", start_date="{start_date}", end_date="{end_date}".
Then run `turnover_risk_scan` with search="{unit_name}".

Produce a concise risk brief with three sections:
1) **Availability Risk** — summarise the operational_risk rating, peak absence day, and availability %.
   If risk is 'high' or 'critical', recommend concrete mitigation (e.g. stagger leave, hire contractor cover).
2) **Retention Risk** — list the top 3 at-risk employees by risk_score, citing their specific signals.
   Recommend one targeted action per person (e.g. mandatory leave, 1-on-1 check-in, career conversation).
3) **Summary** — one paragraph suitable for forwarding to the department head."""


def wellbeing_briefing(person_name: str = "the employee") -> str:
    """Generate a wellbeing briefing for a specific employee, showing burnout status and smart rest plan."""
    return f"""Act as a compassionate HR Wellbeing Advisor.

Step 1: Find the employee by calling `person_list` with search="{person_name}" and get their person_id.
Step 2: Call `analyze_employee_wellbeing` with that person_id.
Step 3: Call `get_smart_rest_plan` with the same person_id.

Present a **Wellbeing Report** in this format:

## {person_name} — Wellbeing Report

**Status:** {{burnout_emoji}} {{burnout_status}} (Score: {{burnout_score}})

**Risk Signals:**
{{list each signal with a bullet}}

**Leave Balance:** {{annual_unused}} days remaining
**Last Rest:** {{days_since_last_rest}} days ago

**Bridge Day Opportunities** (best 3):
| Date | Holiday Nearby | Leave Cost | Rest Days | Efficiency |
|------|---------------|-----------|-----------|------------|
{{table rows from bridge_day_opportunities}}

**Smart Rest Plan** (top 3 by efficiency):
| Take Leave | Free Days | Credits | Rest Days | Efficiency |
|------------|-----------|---------|-----------|------------|
{{table rows from top_rest_opportunities}}

**Recommendation:** {{recommendation}}

Speak warmly and empathetically. If the employee is in the Red Zone, gently urge the manager to act."""


def hr_trend_analysis(scope: str = "company") -> str:
    """Full HR trend analysis: turnover risk + payroll anomalies across the organisation."""
    return f"""Act as a Senior HR Analytics Consultant performing a company-wide trend analysis for "{scope}".

Execute these tools in order and wait for each result before proceeding:
1. `turnover_risk_scan` with limit=100 (or search="{scope}" if a department name was given)
2. `payroll_anomaly_detect` with months_back=3

Then synthesise the findings into an Executive HR Trends Report:

**Section 1 — Retention & Burnout Trends**
- Overall risk distribution (% in each risk tier)
- Top 5 highest-risk employees (anonymised if preferred: use initials or role)
- Identified patterns (e.g. "40 % of Engineering has > 20 unused leave days")
- 3 recommended HR interventions ranked by expected impact

**Section 2 — Payroll Integrity**
- Total anomalies found, broken down by type (duplicates vs outliers)
- Top 3 anomalies requiring immediate review (include person and amounts)
- Recommended next steps (finance review, HR audit, etc.)

**Section 3 — Strategic Recommendations**
- Two or three forward-looking actions the HR team should take this quarter
- Flag any areas where the data is insufficient for confident conclusions"""


def manager_dashboard(department_name: str) -> str:
    """Guided prompt generating a morning briefing for a department manager."""
    return f"""Act as an Executive HR Assistant.
Generate a morning briefing for the manager of the `{department_name}` department.
Use `person_list` to fetch the employees in this department.
For those employees, cross-reference their data:
1) Who is on leave today or upcoming this week? (Use `leave_list`)
2) Does anyone have pending approvals? (Use `approval_list` or check status='waiting')
3) Is there any overdue mandatory training?
Output a very succinct, highly readable dashboard-style summary."""


def register(mcp):
    mcp.prompt()(employee_snapshot)
    mcp.prompt()(burnout_analyzer)
    mcp.prompt()(onboarding_plan)
    mcp.prompt()(offboarding_plan)
    mcp.prompt()(bulk_update_assistant)
    mcp.prompt()(hr_capabilities)
    mcp.prompt()(team_risk_brief)
    mcp.prompt()(wellbeing_briefing)
    mcp.prompt()(hr_trend_analysis)
    mcp.prompt()(manager_dashboard)
