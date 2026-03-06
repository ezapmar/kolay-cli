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

from typing import Any

from fastmcp import FastMCP

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
def person_view(person_id: str) -> dict[str, Any]:
    """View the full profile of a specific employee.

    Args:
        person_id: Employee UUID (get from person_list).

    Returns:
        Full employee profile dict.
    """
    return person_svc.view_person(person_id)


@mcp.tool
def person_summary(person_id: str) -> dict[str, Any]:
    """View a condensed summary of an employee (name, contact, custom fields).

    Args:
        person_id: Employee UUID.
    """
    return person_svc.summary(person_id)


@mcp.tool
def person_leave_status(person_id: str) -> list[dict[str, Any]]:
    """View current leave balances for an employee (used, upcoming, remaining).

    Args:
        person_id: Employee UUID.
    """
    return person_svc.leave_status(person_id)


@mcp.tool
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
def leave_view(leave_id: str) -> dict[str, Any]:
    """View full details of a leave record including workflow status.

    Args:
        leave_id: Leave record UUID (get from leave_list).
    """
    return leave_svc.view_leave(leave_id)


@mcp.tool
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
def timelog_view(timelog_id: str) -> dict[str, Any]:
    """View details and approval workflow for a specific timelog entry.

    Args:
        timelog_id: Timelog UUID (get from timelog_list).
    """
    return timelog_svc.view_timelog(timelog_id)


@mcp.tool
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
def training_view(training_id: str) -> dict[str, Any]:
    """View full details of a specific training in the catalogue.

    Args:
        training_id: Training UUID (get from training_list).
    """
    return training_svc.view_training(training_id)


@mcp.tool
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
def training_delete(training_id: str) -> dict[str, Any]:
    """Remove a training from the catalogue. Irreversible.

    Args:
        training_id: Training UUID.
    """
    return training_svc.delete_training(training_id)


@mcp.tool
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
def transaction_view(transaction_id: str) -> dict[str, Any]:
    """View full details of a specific transaction.

    Args:
        transaction_id: Transaction UUID (get from transaction_list).
    """
    return transaction_svc.view_transaction(transaction_id)


@mcp.tool
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
def calendar_view(event_id: str) -> dict[str, Any]:
    """View full details of a specific calendar event.

    Args:
        event_id: Event UUID (get from calendar_list).
    """
    return calendar_svc.view_event(event_id)


@mcp.tool
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
def unit_tree() -> list[dict[str, Any]]:
    """Return the full organisational unit tree (departments, locations, teams, etc.).

    Returns:
        List of root unit nodes, each may contain 'children' and 'items'.
    """
    return unit_svc.unit_tree()


@mcp.tool
def approval_list() -> list[dict[str, Any]]:
    """List all approval workflows configured for the company.

    Returns:
        List of approval process dicts with 'name', 'type', 'steps'.
    """
    return approval_svc.list_approval_processes()


# ════════════════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Kolay IK MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()
