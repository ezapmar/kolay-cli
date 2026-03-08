"""Kolay IK FastMCP server."""
from __future__ import annotations

import os
from typing import Any

# Prevent logs from breaking MCP JSON transport.
os.environ.setdefault("FASTMCP_LOG_LEVEL", "WARNING")
os.environ.setdefault("FASTMCP_SHOW_SERVER_BANNER", "False")

from fastmcp import FastMCP

from .security import require_auth
from .services import person as person_svc
from .services import leave as leave_svc
from .services import timelog as timelog_svc
from .services import training as training_svc
from .services import transaction as transaction_svc
from .services import calendar as calendar_svc
from .services import unit as unit_svc
from .services import approval as approval_svc



mcp = FastMCP(
    name="kolay-ik [Alpha]",
    instructions=(
        "Kolay IK HR platform tools. "
        "Use person_list to find employee IDs before calling other person tools. "
        "For bulk updates, use the `bulk_update_assistant` prompt which enforces human-in-the-loop confirmation. "
        "Dates are YYYY-MM-DD, datetimes are YYYY-MM-DD HH:MM:SS. "
        "All write operations (create/update/delete/terminate) are real and irreversible."
    ),
)




@mcp.tool
@require_auth
def person_list(
    status: str = "active",
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List employees from the company roster. Status is 'active' or 'inactive'. Search by name. Paginated."""
    return person_svc.list_people(page=page, status=status, search=search, limit=limit)


@mcp.tool
@require_auth
def person_view(person_id: str) -> dict[str, Any]:
    """View full profile of an employee. Use person_id from person_list."""
    return person_svc.view_person(person_id)


@mcp.tool
@require_auth
def person_summary(person_id: str) -> dict[str, Any]:
    """View condensed summary of an employee."""
    return person_svc.summary(person_id)


@mcp.tool
@require_auth
def person_leave_status(person_id: str) -> list[dict[str, Any]]:
    """View leave balances for an employee."""
    return person_svc.leave_status(person_id)


@mcp.tool
@require_auth
def person_create(
    first_name: str,
    last_name: str,
    email: str,
    employment_start: str,
    mobile_phone: str | None = None,
) -> dict[str, Any]:
    """Create a new employee record. Dates in YYYY-MM-DD."""
    return person_svc.create_person(
        first_name=first_name, last_name=last_name,
        email=email, employment_start=employment_start,
        mobile_phone=mobile_phone,
    )


@mcp.tool
@require_auth
def person_update(
    person_id: str,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    mobile_phone: str | None = None,
    custom_fields: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Update an employee's profile. Only supplied fields are changed."""
    return person_svc.update_person(
        person_id, first_name=first_name, last_name=last_name,
        email=email, mobile_phone=mobile_phone, custom_fields=custom_fields,
    )


@mcp.tool
@require_auth
def person_terminate(
    person_id: str,
    termination_date: str,
    reason_code: str,
) -> dict[str, Any]:
    """Terminate employee. Dates in YYYY-MM-DD. Reason codes include '03' voluntary, '22' employer."""
    return person_svc.terminate_person(person_id, termination_date=termination_date, reason_code=reason_code)


@mcp.tool
@require_auth
def person_rehire(person_id: str, start_date: str) -> dict[str, Any]:
    """Rehire a previously terminated employee. Dates in YYYY-MM-DD."""
    return person_svc.rehire_person(person_id, start_date=start_date)


@mcp.tool
@require_auth
def update_employee_data(
    person_id: str,
    update_fields: dict[str, str],
) -> dict[str, Any]:
    """Update arbitrary fields on an employee profile. Use raw API field names."""
    if not update_fields:
        return {"error": True, "message": "No fields provided to update."}
    return person_svc.update_person_fields(person_id, update_fields)





@mcp.tool
@require_auth
def leave_list(
    status: str = "approved",
    start: str | None = None,
    end: str | None = None,
    person_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List leave records. Status is 'approved', 'waiting', 'rejected', or 'cancelled'."""
    return leave_svc.list_leaves(status=status, start=start, end=end, person_id=person_id, limit=limit)


@mcp.tool
@require_auth
def leave_view(leave_id: str) -> dict[str, Any]:
    """View details of a leave record."""
    return leave_svc.view_leave(leave_id)


@mcp.tool
@require_auth
def leave_create(
    person_id: str,
    leave_type_id: str,
    start_date: str,
    end_date: str,
    comment: str = "",
) -> dict[str, Any]:
    """Submit a leave request. Dates in YYYY-MM-DD."""
    return leave_svc.create_leave(
        person_id=person_id, leave_type_id=leave_type_id,
        start_date=start_date, end_date=end_date, comment=comment,
    )




@mcp.tool
@require_auth
def timelog_list(
    start: str | None = None,
    end: str | None = None,
    person_id: str | None = None,
    type: str | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List timelogs. Types: 'work', 'overtime', 'remote'."""
    return timelog_svc.list_timelogs(
        start=start, end=end, person_id=person_id,
        type=type, status=status, page=page, limit=limit,
    )


@mcp.tool
@require_auth
def timelog_view(timelog_id: str) -> dict[str, Any]:
    """View timelog entry details."""
    return timelog_svc.view_timelog(timelog_id)


@mcp.tool
@require_auth
def timelog_create(
    person_id: str,
    start: str,
    end: str,
    type: str = "work",
    description: str = "",
) -> dict[str, Any]:
    """Create timelog. Start/End in YYYY-MM-DD HH:MM:SS. Types: 'work', 'overtime', 'remote'."""
    return timelog_svc.create_timelog(
        person_id=person_id, start=start, end=end,
        type=type, description=description,
    )


@mcp.tool
@require_auth
def timelog_delete(timelog_id: str) -> dict[str, Any]:
    """Delete a timelog record."""
    return timelog_svc.delete_timelog(timelog_id)




@mcp.tool
@require_auth
def training_list(
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List trainings in the catalogue."""
    return training_svc.list_trainings(search=search, page=page, limit=limit)


@mcp.tool
@require_auth
def training_view(training_id: str) -> dict[str, Any]:
    """View training details."""
    return training_svc.view_training(training_id)


@mcp.tool
@require_auth
def training_create(name: str, description: str = "", duration: str = "") -> dict[str, Any]:
    """Add training to the catalogue. Duration is days string."""
    return training_svc.create_training(name=name, description=description, duration=duration)


@mcp.tool
@require_auth
def training_delete(training_id: str) -> dict[str, Any]:
    """Remove training from catalogue."""
    return training_svc.delete_training(training_id)


@mcp.tool
@require_auth
def person_assign_training(
    person_id: str,
    training_id: str,
    status: str = "waiting",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Assign training to employee. Status: 'waiting' or 'approved'."""
    return person_svc.assign_training(
        person_id=person_id, training_id=training_id,
        status=status, start_date=start_date, end_date=end_date,
    )




@mcp.tool
@require_auth
def transaction_list(
    person_id: str | None = None,
    type: str | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List transactions. Types: 'expense', 'bonus', 'advancePayment', 'premium', 'otherCut'."""
    return transaction_svc.list_transactions(
        person_id=person_id, type=type, status=status,
        page=page, limit=limit,
    )


@mcp.tool
@require_auth
def transaction_view(transaction_id: str) -> dict[str, Any]:
    """View transaction details."""
    return transaction_svc.view_transaction(transaction_id)


@mcp.tool
@require_auth
def transaction_create(
    person_id: str,
    type: str,
    amount: float,
    date: str,
    currency: str = "TL",
    description: str = "",
) -> dict[str, Any]:
    """Create transaction. Types: 'expense', 'bonus', 'advancePayment', 'premium', 'otherCut'."""
    return transaction_svc.create_transaction(
        person_id=person_id, type=type, amount=amount,
        date=date, currency=currency, description=description,
    )


@mcp.tool
@require_auth
def transaction_delete(transaction_id: str) -> dict[str, Any]:
    """Delete transaction."""
    return transaction_svc.delete_transaction(transaction_id)




@mcp.tool
@require_auth
def calendar_list(
    start: str | None = None,
    end: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List calendar events. Dates in YYYY-MM-DD."""
    return calendar_svc.list_events(start=start, end=end, search=search, page=page, limit=limit)


@mcp.tool
@require_auth
def calendar_view(event_id: str) -> dict[str, Any]:
    """View event details."""
    return calendar_svc.view_event(event_id)


@mcp.tool
@require_auth
def calendar_create(
    title: str,
    start: str,
    end: str,
    comment: str = "",
) -> dict[str, Any]:
    """Create calendar event. Dates in YYYY-MM-DD HH:MM:SS."""
    return calendar_svc.create_event(title=title, start=start, end=end, comment=comment)


@mcp.tool
@require_auth
def calendar_update(
    event_id: str,
    title: str | None = None,
    start: str | None = None,
    end: str | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    """Update calendar event. Only supplied fields are changed."""
    return calendar_svc.update_event(event_id, title=title, start=start, end=end, comment=comment)


@mcp.tool
@require_auth
def calendar_delete(event_id: str) -> dict[str, Any]:
    """Delete calendar event."""
    return calendar_svc.delete_event(event_id)




@mcp.tool
@require_auth
def unit_tree() -> list[dict[str, Any]]:
    """Return organisational unit tree."""
    return unit_svc.unit_tree()


@mcp.tool
@require_auth
def approval_list() -> list[dict[str, Any]]:
    """List approval workflows."""
    return approval_svc.list_approval_processes()




@mcp.prompt()
def employee_snapshot(person_query: str) -> str:
    """Generate HR snapshot and leave balance report for an employee."""
    return f"""Act as an HR Manager.
Use the `person_list` tool to find the exact ID for the employee matching "{person_query}".
Then, use `person_view` and `person_leave_status` to gather their data.
Output a clean Markdown report with:
1) ID Card (Name, Department, Title)
2) Tenure (calculated precisely from employmentStartDate)
3) A list of leaves where 'unused' > 0 (specifically highlighting Annual Leave)."""


@mcp.prompt()
def burnout_analyzer(department_name: str) -> str:
    """Analyze a department for burnout risk based on unused annual leave."""
    return f"""Act as an Employee Engagement Specialist.
Use the `person_list` tool (with an empty search or a specific one) to find all employees working in the `{department_name}` department.
Use the `person_leave_status` tool for each of these employees to check their Annual Leave balances (where `primary` is true).
Output a report highlighting employees with severe burnout risk (unused Annual Leave > 20 days).
Draft a professional email to their department manager suggesting they encourage these specific employees to take time off."""


@mcp.prompt()
def onboarding_plan(person_query: str) -> str:
    """Draft onboarding kit for a new hire."""
    return f"""Act as an Onboarding Specialist.
First, use the `person_list` tool with search="{person_query}" to find the employee. If multiple results are returned, pick the closest match by name.
Then use `person_view` with their ID to retrieve the exact Name, Department, and Title for the new hire.
Based on their profile and role, output 3 things:
1) A warm, energetic welcome email draft to be sent to the whole company.
2) A precise guessed IT Setup and Hardware checklist tailored to their specific Title and Department.
3) A first-week 30-minute introductory meeting schedule draft mapping out key department roles they should meet."""


@mcp.prompt()
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


@mcp.prompt()
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

**Step 3 — ⚠️ MANDATORY CONFIRMATION — DO NOT SKIP:**
STOP. Do NOT call any update tools yet.
Present this Markdown table to the user:

| # | Full Name | Current `{target_field}` | Will change to |
|---|-----------|--------------------------|----------------|
(one row per matched employee)

Then ask EXACTLY this question:
"Do you confirm updating `{target_field}` for these **N** employees from \\"{old_value}\\" → \\"{new_value}\\"? (Yes / No)"

**Step 4 — Execute (only on explicit "Yes"):**
• If the user responds with "Yes": loop through each matched employee and call `update_employee_data` with their ID and {{"{target_field}": "{new_value}"}}.
  Confirm each update as it completes (e.g. "✅ Updated Ahmet Yılmaz").
• If the user responds with anything other than "Yes": abort immediately and state "Operation cancelled. No changes were made."

**Step 5 — Final Summary:**
Present a concise summary: total scanned, total updated (or 0 if cancelled), any errors."""




if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Kolay IK MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "http":
        print(f"\n🔌 Kolay IK MCP server  http://{args.host}:{args.port}/mcp\n")
        mcp.run(transport="http", host=args.host, port=args.port)
    elif sys.stdin.isatty():
        # User ran `kolay-mcp` directly in a terminal — give them guidance
        print(
            "\n"
            "  Kolay IK MCP Server\n"
            "\n"
            "  This binary is for AI clients (Claude, Cursor, Gemini CLI).\n"
            "  You probably want the CLI instead:  kolay --help\n"
            "\n"
            "  To start manually:\n"
            "    kolay mcp serve                        # STDIO (local)\n"
            "    kolay mcp serve --transport http       # HTTP (network)\n"
            "\n"
            "  To configure Claude Desktop, add to config:\n"
            '    { "mcpServers": { "kolay-ik": { "command": "kolay-mcp" } } }\n'
        )
    else:
        mcp.run()

