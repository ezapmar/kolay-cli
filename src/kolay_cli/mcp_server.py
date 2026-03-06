"""
Kolay IK — FastMCP server.

Exposes every major Kolay IK operation as an MCP tool so that LLMs,
agents, and MCP-aware clients (Claude Desktop, Cursor, Gemini CLI …)
can call Kolay IK without touching the CLI.

Run locally (STDIO, default):
    python -m kolay_cli.mcp_server

Run as HTTP server:
    python -m kolay_cli.mcp_server --transport http --port 8000

Or via the CLI:
    kolay mcp serve [--transport http] [--port 8000]
"""
from __future__ import annotations

import os
from typing import Any

# Disable fastmcp's stdout logs and banner out-of-the-box
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

# ── Server ────────────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="kolay-ik",
    instructions=(
        "Kolay IK HR platform tools. "
        "Use person_list to find employee IDs before calling other person tools. "
        "Dates are YYYY-MM-DD, datetimes are YYYY-MM-DD HH:MM:SS. "
        "All write operations (create/update/delete/terminate) are real and irreversible."
    ),
)


# ════════════════════════════════════════════════════════════════════════════
# PEOPLE
# ════════════════════════════════════════════════════════════════════════════

@mcp.tool
@require_auth
def person_list(
    status: str = "active",
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List employees from the company roster.

    Args:
        status: 'active' or 'inactive'. Defaults to 'active'.
        search: Optional name/email search term.
        page: Page number (1-based).
        limit: Max records per page (default 20).

    Returns:
        dict with keys: items (list of employee dicts), totalCount, page.
    """
    return person_svc.list_people(page=page, status=status, search=search, limit=limit)


@mcp.tool
@require_auth
def person_view(person_id: str) -> dict[str, Any]:
    """View the full profile of a specific employee.

    Args:
        person_id: Employee UUID (get from person_list).

    Returns:
        Full employee profile dict.
    """
    return person_svc.view_person(person_id)


@mcp.tool
@require_auth
def person_summary(person_id: str) -> dict[str, Any]:
    """View a condensed summary of an employee (name, contact, custom fields).

    Args:
        person_id: Employee UUID.
    """
    return person_svc.summary(person_id)


@mcp.tool
@require_auth
def person_leave_status(person_id: str) -> list[dict[str, Any]]:
    """View current leave balances for an employee (used, upcoming, remaining).

    Args:
        person_id: Employee UUID.
    """
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
    """Create a new employee record.

    Args:
        first_name: First name.
        last_name: Last name.
        email: Work email address.
        employment_start: Employment start date (YYYY-MM-DD).
        mobile_phone: Optional mobile phone number.

    Returns:
        dict with 'id' of the created employee.
    """
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
    """Update an employee's profile. Only supplied fields are changed.

    Args:
        person_id: Employee UUID.
        first_name: New first name (optional).
        last_name: New last name (optional).
        email: New work email (optional).
        mobile_phone: New mobile phone (optional).
        custom_fields: Dict of {fieldToken: value} for custom data fields (optional).

    Returns:
        dict with 'status': 'updated'.
    """
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
    """Terminate the employment of an employee. Irreversible.

    Args:
        person_id: Employee UUID.
        termination_date: Date of termination (YYYY-MM-DD).
        reason_code: SGK reason code. Common codes:
            '03' voluntary resignation,
            '22' termination by employer,
            '11' retirement,
            '04' termination without notice,
            '30' other.

    Returns:
        dict with 'status': 'terminated'.
    """
    return person_svc.terminate_person(person_id, termination_date=termination_date, reason_code=reason_code)


@mcp.tool
@require_auth
def person_rehire(person_id: str, start_date: str) -> dict[str, Any]:
    """Rehire a previously terminated employee.

    Args:
        person_id: Employee UUID.
        start_date: New employment start date (YYYY-MM-DD).
    """
    return person_svc.rehire_person(person_id, start_date=start_date)


# ════════════════════════════════════════════════════════════════════════════
# LEAVE
# ════════════════════════════════════════════════════════════════════════════

@mcp.tool
@require_auth
def leave_list(
    status: str = "approved",
    start: str | None = None,
    end: str | None = None,
    person_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List leave records.

    Args:
        status: 'approved', 'waiting', 'rejected', or 'cancelled'. Default 'approved'.
        start: Start date filter (YYYY-MM-DD). Defaults to Jan 1 of current year.
        end: End date filter (YYYY-MM-DD). Defaults to Dec 31 of current year.
        person_id: Filter by employee UUID (optional).
        limit: Max records (default 50).

    Returns:
        List of leave record dicts.
    """
    return leave_svc.list_leaves(status=status, start=start, end=end, person_id=person_id, limit=limit)


@mcp.tool
@require_auth
def leave_view(leave_id: str) -> dict[str, Any]:
    """View full details of a leave record including workflow status.

    Args:
        leave_id: Leave record UUID (get from leave_list).
    """
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
    """Submit a leave request for an employee.

    Args:
        person_id: Employee UUID.
        leave_type_id: Leave type UUID (get from person_leave_status to see available types).
        start_date: Leave start date (YYYY-MM-DD).
        end_date: Leave end date (YYYY-MM-DD).
        comment: Optional comment.

    Returns:
        dict with 'status': 'created'.
    """
    return leave_svc.create_leave(
        person_id=person_id, leave_type_id=leave_type_id,
        start_date=start_date, end_date=end_date, comment=comment,
    )


# ════════════════════════════════════════════════════════════════════════════
# TIMELOGS
# ════════════════════════════════════════════════════════════════════════════

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
    """List timelog records (work hours, overtime, remote work).

    Args:
        start: Start date (YYYY-MM-DD). Defaults to Jan 1 of current year.
        end: End date (YYYY-MM-DD). Defaults to Dec 31 of current year.
        person_id: Filter by employee UUID (optional).
        type: Filter by type: 'work', 'overtime', 'remote' (optional).
        status: Filter by status: 'waiting', 'approved', 'rejected' (optional).
        page: Page number.
        limit: Records per page (default 20).

    Returns:
        dict with 'items', 'totalCount', 'page'.
    """
    return timelog_svc.list_timelogs(
        start=start, end=end, person_id=person_id,
        type=type, status=status, page=page, limit=limit,
    )


@mcp.tool
@require_auth
def timelog_view(timelog_id: str) -> dict[str, Any]:
    """View details and approval workflow for a specific timelog entry.

    Args:
        timelog_id: Timelog UUID (get from timelog_list).
    """
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
    """Submit a new timelog entry for approval.

    Args:
        person_id: Employee UUID.
        start: Start datetime (YYYY-MM-DD HH:MM:SS).
        end: End datetime (YYYY-MM-DD HH:MM:SS).
        type: 'work', 'overtime', or 'remote'. Default 'work'.
        description: Optional description.

    Returns:
        dict with 'status': 'created'.
    """
    return timelog_svc.create_timelog(
        person_id=person_id, start=start, end=end,
        type=type, description=description,
    )


@mcp.tool
@require_auth
def timelog_delete(timelog_id: str) -> dict[str, Any]:
    """Permanently delete a timelog record. Irreversible.

    Args:
        timelog_id: Timelog UUID.
    """
    return timelog_svc.delete_timelog(timelog_id)


# ════════════════════════════════════════════════════════════════════════════
# TRAINING CATALOGUE
# ════════════════════════════════════════════════════════════════════════════

@mcp.tool
@require_auth
def training_list(
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List all trainings in the company catalogue.

    Args:
        search: Optional name search term.
        page: Page number.
        limit: Records per page.

    Returns:
        dict with 'items', 'totalCount'.
    """
    return training_svc.list_trainings(search=search, page=page, limit=limit)


@mcp.tool
@require_auth
def training_view(training_id: str) -> dict[str, Any]:
    """View full details of a specific training in the catalogue.

    Args:
        training_id: Training UUID (get from training_list).
    """
    return training_svc.view_training(training_id)


@mcp.tool
@require_auth
def training_create(name: str, description: str = "", duration: str = "") -> dict[str, Any]:
    """Add a new training to the company catalogue.

    Args:
        name: Training name (required).
        description: Optional description.
        duration: Optional duration in days (as string, e.g. '3').

    Returns:
        dict with 'status': 'created'.
    """
    return training_svc.create_training(name=name, description=description, duration=duration)


@mcp.tool
@require_auth
def training_delete(training_id: str) -> dict[str, Any]:
    """Remove a training from the catalogue. Irreversible.

    Args:
        training_id: Training UUID.
    """
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
    """Assign a training from the catalogue to an employee.

    Args:
        person_id: Employee UUID.
        training_id: Training UUID (get from training_list).
        status: 'waiting' or 'approved'. Default 'waiting'.
        start_date: Assignment start date (YYYY-MM-DD, optional).
        end_date: Assignment end date (YYYY-MM-DD, optional).
    """
    return person_svc.assign_training(
        person_id=person_id, training_id=training_id,
        status=status, start_date=start_date, end_date=end_date,
    )


# ════════════════════════════════════════════════════════════════════════════
# TRANSACTIONS
# ════════════════════════════════════════════════════════════════════════════

@mcp.tool
@require_auth
def transaction_list(
    person_id: str | None = None,
    type: str | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List financial transactions (expenses, bonuses, advances, cuts).

    Args:
        person_id: Filter by employee UUID (optional).
        type: Filter by type: 'expense', 'bonus', 'advancePayment', 'premium',
              'otherCut', 'militaryBenefit', etc. (optional).
        status: Filter by status: 'waiting', 'approved' (optional).
        page: Page number.
        limit: Records per page.

    Returns:
        dict with 'items', 'totalCount', 'page'.
    """
    return transaction_svc.list_transactions(
        person_id=person_id, type=type, status=status,
        page=page, limit=limit,
    )


@mcp.tool
@require_auth
def transaction_view(transaction_id: str) -> dict[str, Any]:
    """View full details of a specific transaction.

    Args:
        transaction_id: Transaction UUID (get from transaction_list).
    """
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
    """Create a financial transaction (bonus, expense, advance, cut, etc.).

    Args:
        person_id: Employee UUID.
        type: Transaction type. Options: 'expense', 'bonus', 'advancePayment',
              'premium', 'otherCut', 'militaryBenefit', 'fuelAllowanceBenefit'.
        amount: Amount as a number.
        date: Transaction date (YYYY-MM-DD).
        currency: Currency code (default 'TL').
        description: Optional description.

    Returns:
        dict with 'status': 'created'.
    """
    return transaction_svc.create_transaction(
        person_id=person_id, type=type, amount=amount,
        date=date, currency=currency, description=description,
    )


@mcp.tool
@require_auth
def transaction_delete(transaction_id: str) -> dict[str, Any]:
    """Permanently delete a transaction record. Irreversible.

    Args:
        transaction_id: Transaction UUID.
    """
    return transaction_svc.delete_transaction(transaction_id)


# ════════════════════════════════════════════════════════════════════════════
# CALENDAR
# ════════════════════════════════════════════════════════════════════════════

@mcp.tool
@require_auth
def calendar_list(
    start: str | None = None,
    end: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List calendar events for a given period.

    Args:
        start: Start date (YYYY-MM-DD). Defaults to today.
        end: End date (YYYY-MM-DD). Defaults to 30 days from now.
        search: Optional title keyword search.
        page: Page number.
        limit: Records per page.

    Returns:
        dict with 'items', 'totalCount', 'page'.
    """
    return calendar_svc.list_events(start=start, end=end, search=search, page=page, limit=limit)


@mcp.tool
@require_auth
def calendar_view(event_id: str) -> dict[str, Any]:
    """View full details of a specific calendar event.

    Args:
        event_id: Event UUID (get from calendar_list).
    """
    return calendar_svc.view_event(event_id)


@mcp.tool
@require_auth
def calendar_create(
    title: str,
    start: str,
    end: str,
    comment: str = "",
) -> dict[str, Any]:
    """Create a new calendar event.

    Args:
        title: Event title.
        start: Start datetime (YYYY-MM-DD HH:MM:SS).
        end: End datetime (YYYY-MM-DD HH:MM:SS).
        comment: Optional description.

    Returns:
        dict with 'id' of the created event.
    """
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
    """Update an existing calendar event. Only provided fields are changed.

    Args:
        event_id: Event UUID.
        title: New title (optional).
        start: New start datetime (optional).
        end: New end datetime (optional).
        comment: New comment (optional).
    """
    return calendar_svc.update_event(event_id, title=title, start=start, end=end, comment=comment)


@mcp.tool
@require_auth
def calendar_delete(event_id: str) -> dict[str, Any]:
    """Permanently delete a calendar event. Irreversible.

    Args:
        event_id: Event UUID.
    """
    return calendar_svc.delete_event(event_id)


# ════════════════════════════════════════════════════════════════════════════
# ORGANISATION
# ════════════════════════════════════════════════════════════════════════════

@mcp.tool
@require_auth
def unit_tree() -> list[dict[str, Any]]:
    """Return the full organisational unit tree (departments, locations, teams, etc.).

    Returns:
        List of root unit nodes, each may contain 'children' and 'items'.
    """
    return unit_svc.unit_tree()


@mcp.tool
@require_auth
def approval_list() -> list[dict[str, Any]]:
    """List all approval workflows configured for the company.

    Returns:
        List of approval process dicts with 'name', 'type', 'steps'.
    """
    return approval_svc.list_approval_processes()


# ════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ════════════════════════════════════════════════════════════════════════════

@mcp.prompt()
def employee_snapshot(person_query: str) -> str:
    """Generate a comprehensive HR snapshot and leave balance report for an employee."""
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
def onboarding_plan(person_id: str) -> str:
    """Draft an onboarding kit including welcome emails and schedules for a new hire."""
    return f"""Act as an Onboarding Specialist.
Use the `person_view` tool to retrieve the exact Name, Department, and Title for the new hire with ID `{person_id}`.
Based on their profile and role, output 3 things:
1) A warm, energetic welcome email draft to be sent to the whole company.
2) A precise guessed IT Setup and Hardware checklist tailored to their specific Title and Department.
3) A first-week 30-minute introductory meeting schedule draft mapping out key department roles they should meet."""


@mcp.prompt()
def offboarding_plan(person_id: str) -> str:
    """Draft an offboarding action plan with payout calculations and exit questions."""
    return f"""Act as an HR Operations Specialist.
Use the `person_view` and `person_leave_status` tools to retrieve the full profile and leave balances for the departing employee with ID `{person_id}`.
Review their 'unused' Annual Leave balance specifically.
Output an Offboarding Action Plan including:
1) The exact number of unused Annual Leave days that remain to be paid out.
2) A role-specific knowledge handover checklist based on their exact Title.
3) 5 strategic Exit Interview questions tailored specifically to their Department so they feel heard."""


# ════════════════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════════════════

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

