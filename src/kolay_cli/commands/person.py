from __future__ import annotations
import os
from typing import Any
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

from ..api import KolayClient, APIError, safe_id
from ..services import person as svc
from ..ui import (
    console, short_id, display_status, fmt_val, fmt_num, label, fmt_datetime,
    print_error, print_success, print_fetching, print_empty, kv_table,
    print_next_steps, print_pagination_footer,
    confirm_destructive_action, print_irreversible_warning,
    save_page_state, load_page_state,
    pick_person, pick_training, pick_person_training, pick_person_file,
    api_call, recoverable_api_call, no_command_help, PRIMARY, filter_items,
    validate_date, prompt_date,
    is_json_mode, is_yes_mode, json_output, json_error, require_arg, resolve_row, global_to_page_relative,
)

app = typer.Typer(help="Manage person/employee records in Kolay.")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


@app.command(name="list")
def list_people(
    page: int = typer.Option(1, help="Page number"),
    status: str = typer.Option("active", help="Filter by status: active, inactive"),
    search: str | None = typer.Option(None, "--search", "-s", help="Search by name or email"),
    filter: str | None = typer.Option(None, "--filter", "-f", help="Filter locally by name or email"),
    limit: int = typer.Option(20, help="Number of records to show")
) -> None:
    """List employees from the company roster.
    
    Defaults to active employees. Can be filtered by status or searched by name/email.
    """
    with api_call(f"Fetching {status} employees..."):
        result = svc.list_people(page=page, status=status, search=search, limit=limit)
        items = result["items"]
        total = result["totalCount"]

    if is_json_mode():
        json_output(result)
        return

    if not items:
        print_empty(f"{status} employees", hint="Try --status inactive to find terminated employees.")
        return

    items = filter_items(
        items, filter,
        [
            lambda p: f"{p.get('firstName', '')} {p.get('lastName', '')}",
            lambda p: p.get("workEmail") or p.get("email") or "",
        ],
        label="employees",
    )

    title = f"{status.title()} Employees"
    if search:
        title += f" matching '{search}'"
    if filter:
        title += f" filtered by '{filter}'"

    console.print(f"\n[bold {PRIMARY}]{title}[/bold {PRIMARY}]\n")

    table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
    table.add_column("#", style="grey62", justify="right", width=4)
    table.add_column("Name", style="bold white", min_width=22)
    table.add_column("Email", style="grey85")
    table.add_column("Phone", style="grey62")
    table.add_column("Short ID", style="grey62")

    for i, person in enumerate(items, 1):
        row_num = (page - 1) * limit + i
        name = f"{person.get('firstName', '')} {person.get('lastName', '')}".strip() or person.get("name", "—")
        email = person.get("workEmail") or person.get("email") or "—"
        phone = person.get("mobilePhone") or "—"
        table.add_row(
            str(row_num),
            name, email, phone,
            short_id(str(person.get("id", "")))
        )

    console.print(table)
    _extra = f"--status {status}"
    if search:
        _extra += f" --search \"{search}\""
    print_pagination_footer(
        command="kolay person list",
        page=page, limit=limit, shown=len(items), total=total,
        extra_flags=_extra,
    )
    save_page_state(resource="person", page=page, limit=limit, total=total)
    print_next_steps([
        ("kolay person view <#>", "View full profile"),
        ("kolay person list --search <name>", "Search by name/email"),
        ("kolay person create", "Add a new employee"),
    ])


def _resolve_person_id(value: str, *, status: str = "active", limit: int = 50) -> str:
    """Resolve a row-number shorthand (e.g. '21') to a real person UUID.

    Honours the last-listed page: if the user ran ``kolay person list --page 2``
    (seeing rows 21–40), then types ``kolay person view 21``, this correctly
    fetches page 2 and resolves the page-relative index (1) item 1 of page 2.
    Falls back to page 1 when no recent state is found.
    """
    if not value.isdigit():
        return value
    state = load_page_state("person")
    if state and state["page"] > 1:
        page_rel = global_to_page_relative(int(value), page=state["page"], limit=state["limit"])
        result = svc.list_people(page=state["page"], status=status, limit=state["limit"])
        return resolve_row(str(page_rel), result["items"], label="employee")
    result = svc.list_people(page=1, status=status, limit=limit)
    return resolve_row(value, result["items"], label="employee")


@app.command(name="view")
def view_person(person_id: str | None = typer.Argument(None, help="ID or row number of the person to view")) -> None:
    """View the full profile of a specific employee.

    Pass the UUID or the row number shown by ``kolay person list`` (e.g. 1, 5).
    If no ID is provided, an interactive picker will be shown.
    """
    require_arg(person_id, "person-id")
    if not person_id:
        person_id = pick_person()

    with api_call("Fetching person details..."):
        person_id = _resolve_person_id(person_id)
        data = svc.view_person(person_id)

    if is_json_mode():
        json_output(data)
        return

    fname = data.get("firstName", "")
    lname = data.get("lastName", "")
    st = data.get("status", "")
    email = data.get("workEmail") or data.get("email") or "—"

    console.print(f"\n[bold {PRIMARY}]Employee Profile[/bold {PRIMARY}] [bold white]{fname} {lname}[/bold white]")
    console.print(f" {display_status(st)}  [grey62]{email}[/grey62]\n")

    SECTIONS = {
        "Identity": ["tckn", "birthDate", "gender", "maritalStatus", "bloodType"],
        "Employment": ["employmentStart", "employmentEnd", "department", "title", "manager", "managerId", "workerType", "contractType", "jobType"],
        "Contact": ["mobilePhone", "workPhone", "homePhone", "address"],
        "Internal": ["id", "shortId", "companyId", "createdAt", "updatedAt"],
    }

    mapped_keys = [k for group in SECTIONS.values() for k in group]
    exclude_core = ["id", "firstName", "lastName", "status", "workEmail", "email", "units"]
    
    for sec_name, attrs in SECTIONS.items():
        subset = {k: data[k] for k in attrs if k in data and data[k]}
        if subset:
            console.print(f"\n[bold {PRIMARY}]{sec_name}[/bold {PRIMARY}]")
            console.print(Panel(kv_table(subset), border_style=PRIMARY, expand=False))

    other_subset = {k: v for k, v in data.items() if k not in mapped_keys and k not in exclude_core and v}
    if other_subset:
        console.print(f"\n[bold {PRIMARY}]Other Details[/bold {PRIMARY}]")
        console.print(Panel(kv_table(other_subset), border_style=PRIMARY, expand=False))
    
    # Display Unit Details if available
    units = data.get("units", [])
    if units:
        console.print("\n[bold magenta]Organisational Units[/bold magenta]")
        u_tbl = Table(header_style="bold magenta", border_style="magenta", box=None, show_edge=False)
        u_tbl.add_column("Type", style="grey62")
        u_tbl.add_column("Item", style="bold white")
        u_tbl.add_column("Primary?", justify="center")
        
        for u in units:
            items = u.get("items", [])
            for item in items:
                u_tbl.add_row(
                    item.get("unitName", "—"),
                    item.get("unitItemName", "—"),
                    "[green]Yes[/green]" if u.get("primary", False) else "[grey62]No[/grey62]"
                )
        console.print(u_tbl)
    
    console.print()


@app.command(name="leave-status")
def view_leave_status(
    person_id: str | None = typer.Argument(None, help="ID of the person to view leave balances for")
) -> None:
    """View current leave balances and limits for a specific employee.
    
    Shows used, upcoming, and remaining days for all assigned leave types.
    """
    require_arg(person_id, "person-id")
    if not person_id:
        person_id = pick_person()

    with api_call("Fetching leave balances..."):
        data = svc.leave_status(person_id)

    if is_json_mode():
        json_output(data)
        return
    if not data:
        print_empty("leave balances")
        return

    table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
    table.add_column("Leave Type", style="bold white", min_width=20)
    table.add_column("Limit", justify="right")
    table.add_column("Used", justify="right", style="orange1")
    table.add_column("Upcoming", justify="right", style="grey85")
    table.add_column("Remaining", justify="right", style="bold green")

    for item in data:
        ltype = item.get("leaveType", {})
        name = ltype.get("name", "—")
        table.add_row(
            name,
            fmt_num(item.get("dayLimit", "∞")),
            fmt_num(item.get("used", 0)),
            fmt_num(item.get("totalUpcoming", 0)),
            fmt_num(item.get("unused", 0))
        )

    console.print(f"\n[bold {PRIMARY}]Leave Balances[/bold {PRIMARY}]\n")
    console.print(table)
    console.print()


@app.command(name="terminate")
def terminate_person(
    person_id: str | None = typer.Argument(None, help="ID of the person to terminate"),
    termination_date: str | None = typer.Option(
        None, help="Termination date (YYYY-MM-DD). Defaults to today."
    ),
    reason: str | None = typer.Option(
        None, help="Reason code (e.g. 01 for resignation). Leave blank to see options."
    ),
) -> None:
    """Terminate the employment of a specific employee.

    Will prompt for the termination date and reason if not provided as options.
    """
    from ..api.errors import APIError
    from ..ui.formatters import recoverable_api_call

    require_arg(person_id, "person-id")
    if not person_id:
        person_id = pick_person()

    # Remember the resolved employee name for use in prompts/errors
    try:
        person_data = svc.view_person(person_id)
        emp_name = f"{person_data.get('firstName', '')} {person_data.get('lastName', '')}".strip()
    except Exception:
        person_data = {}
        emp_name = ""
    display_name = emp_name or short_id(person_id)

    if termination_date:
        termination_date = validate_date(termination_date)
    else:
        if is_json_mode():
            require_arg(None, "termination-date")
        from datetime import datetime
        default_date = datetime.now().strftime("%Y-%m-%d")
        termination_date = prompt_date("Termination date", default=default_date)

    if not reason:
        if is_json_mode():
            require_arg(None, "reason")
        console.print("\n[bold white]  Termination reasons:[/bold white]")
        for code, desc in svc.REASON_CODES.items():
            console.print(f" [cyan]{code}[/cyan] : {desc}")
        reason = typer.prompt("\n  Enter reason code", type=str)

    # 3.3: Show full termination details before confirming — reason code has
    # legal implications under Turkish labour law (SGK reporting).
    reason_desc = svc.REASON_CODES.get(reason, f"Unknown code ({reason})")
    confirm_destructive_action(
        action=f"Terminate {display_name}",
        details=[
            ("Employee", display_name),
            ("Reason", f"{reason} — {reason_desc}"),
            ("Effective date", termination_date),
        ],
        warning="This will be reported to SGK. Ensure the reason code is correct.",
    )

    try:
        with recoverable_api_call("Processing termination..."):
            result = svc.terminate_person(person_id, termination_date=termination_date, reason_code=reason)
    except APIError as exc:
        _handle_terminate_error(exc, person_id=person_id, display_name=display_name,
                                termination_date=termination_date, reason=reason)
        return

    if is_json_mode():
        json_output(result)
    else:
        print_success("Employee terminated successfully.")
        print_irreversible_warning()


def _handle_terminate_error(
    exc: "Any",
    *,
    person_id: str,
    display_name: str,
    termination_date: str | None = None,
    reason: str | None = None,
) -> None:
    """Offer recovery options after a termination API error."""
    from ..api.errors import APIError
    import typer

    msg = str(exc.message if hasattr(exc, "message") else exc).lower()
    has_pending = "talep" in msg or "pending" in msg or "onay" in msg or "bekley" in msg

    console.print()
    if has_pending:
        console.print(
            f" [bold yellow]Tip:[/bold yellow] [bold]{display_name}[/bold] has pending "
            "requests that must be resolved before termination.\n"
            " Approve, reject, or delete them, then try again."
        )
    else:
        console.print(
            " [bold yellow]What would you like to do?[/bold yellow]"
        )

    console.print()
    console.print(f" [cyan]1[/cyan]  Show pending leave requests for {display_name}")
    console.print(f" [cyan]2[/cyan]  Show pending timelog requests for {display_name}")
    console.print(f" [cyan]3[/cyan]  Pick a different employee to terminate")
    console.print(f" [cyan]4[/cyan]  Abort")
    console.print()

    choice = typer.prompt(" Choose an option", default="4").strip()

    if choice == "1":
        # Show pending leaves for this person
        try:
            from ..services import leave as leave_svc
            leaves = leave_svc.list_leaves(status="waiting", person_id=person_id, limit=20)
            if not leaves:
                console.print(f"\n  [grey62]No pending leave requests found for {display_name}.[/grey62]\n")
            else:
                from rich.table import Table
                console.print(f"\n  [bold white]Pending leave requests for {display_name}:[/bold white]\n")
                tbl = Table(box=None, show_edge=False, header_style=f"bold {PRIMARY}")
                tbl.add_column("#", style="grey62", width=4, justify="right")
                tbl.add_column("Type", style="bold white")
                tbl.add_column("Start", style="grey62")
                tbl.add_column("End", style="grey62")
                tbl.add_column("Short ID", style="grey62")
                for i, lv in enumerate(leaves, 1):
                    ltype = (lv.get("leaveType") or {}).get("name", "—")
                    tbl.add_row(
                        str(i), ltype,
                        fmt_datetime(lv.get("startDate")),
                        fmt_datetime(lv.get("endDate")),
                        short_id(str(lv.get("id", ""))),
                    )
                console.print(tbl)
            console.print(
                f"\n  [grey62]Run [bold]kolay leave list --person-id {person_id} --status waiting[/bold] "
                "to manage them.[/grey62]\n"
            )
        except Exception:
            console.print(f"\n  [grey62]Run: kolay leave list --person-id {person_id} --status waiting[/grey62]\n")

    elif choice == "2":
        # Show pending timelogs for this person
        try:
            from ..services import timelog as timelog_svc
            tls = timelog_svc.list_timelogs(status="waiting", person_id=person_id, limit=20)
            items = tls.get("items", [])
            if not items:
                console.print(f"\n  [grey62]No pending timelog requests found for {display_name}.[/grey62]\n")
            else:
                from rich.table import Table
                console.print(f"\n  [bold white]Pending timelog requests for {display_name}:[/bold white]\n")
                tbl = Table(box=None, show_edge=False, header_style=f"bold {PRIMARY}")
                tbl.add_column("#", style="grey62", width=4, justify="right")
                tbl.add_column("Type", style="bold white")
                tbl.add_column("Start", style="grey62")
                tbl.add_column("End", style="grey62")
                tbl.add_column("Short ID", style="grey62")
                for i, tl in enumerate(items, 1):
                    tbl.add_row(
                        str(i),
                        str(tl.get("type", "—")),
                        fmt_datetime(tl.get("startDate")),
                        fmt_datetime(tl.get("endDate")),
                        short_id(str(tl.get("id", ""))),
                    )
                console.print(tbl)
            console.print(
                f"\n  [grey62]Run [bold]kolay timelog list --person-id {person_id} --status waiting[/bold] "
                "to manage them.[/grey62]\n"
            )
        except Exception:
            console.print(f"\n  [grey62]Run: kolay timelog list --person-id {person_id} --status waiting[/grey62]\n")

    elif choice == "3":
        # Restart with a different employee — carry over date & reason from outer scope
        new_person_id = pick_person()
        terminate_person(
            person_id=new_person_id,
            termination_date=termination_date,
            reason=reason,
        )

    else:
        console.print("\n  [grey62]Aborted.[/grey62]\n")
        raise typer.Exit(1)


@app.command(name="update")
def update_person(
    person_id: str | None = typer.Argument(None, help="ID of the person to update"),
    first_name: str | None = typer.Option(None, "--first-name", help="Update first name"),
    last_name: str | None = typer.Option(None, "--last-name", help="Update last name"),
    email: str | None = typer.Option(None, "--email", help="Update work email address"),
    mobile_phone: str | None = typer.Option(None, "--phone", help="Update mobile phone"),
    custom_field: list[str] | None = typer.Option(
        None, "--custom", help="Custom field as key=value (e.g. --custom adres='Street 33/4')"
    )
) -> None:
    """Update profile details of a specific employee.
    
    Only fields passed as options will be updated.
    """
    require_arg(person_id, "person-id")
    if not person_id:
        person_id = pick_person()

    custom: dict[str, str] | None = None
    if custom_field:
        custom = {}
        for cf in custom_field:
            if "=" in cf:
                k, v = cf.split("=", 1)
                custom[k.strip()] = v.strip()

    if not any([first_name, last_name, email, mobile_phone, custom]):
        print_error("Nothing to update.", hint="Provide at least one option like --first-name.")
        return

    with api_call("Updating person details..."):
        result = svc.update_person(
            person_id,
            first_name=first_name, last_name=last_name,
            email=email, mobile_phone=mobile_phone,
            custom_fields=custom,
        )

    if is_json_mode():
        json_output(result)
    else:
        print_success("Employee profile updated successfully.")


@app.command(name="summary")
def view_summary(person_id: str | None = typer.Argument(None, help="ID of the person to view summary for")) -> None:
    """View a condensed summary of an employee record.
    
    Includes key identity and contact info.
    """
    if not person_id:
        person_id = pick_person()

    with api_call("Fetching summary..."):
        data = svc.summary(person_id)

    if is_json_mode():
        json_output(data)
        return

    fname = data.get("firstName", "")
    lname = data.get("lastName", "")
    
    console.print(f"\n[bold {PRIMARY}]Employee Summary[/bold {PRIMARY}] [bold white]{fname} {lname}[/bold white]\n")
    tbl = kv_table(data, exclude=["id", "firstName", "lastName", "status", "dataList"])
    console.print(Panel(tbl, border_style=PRIMARY, expand=False))
    
    # Custom Fields in Summary
    custom_data = [f for f in data.get("dataList", []) if f.get("value")]
    if custom_data:
        c_tbl = Table(show_header=True, header_style=f"bold {PRIMARY}", box=None, padding=(0, 2, 0, 0))
        c_tbl.add_column("Field", style="grey85")
        c_tbl.add_column("Value")
        for field in custom_data:
            c_tbl.add_row(field.get("fieldToken", "—"), fmt_val(field.get("value")))
        console.print(Panel(c_tbl, title="Custom Fields", border_style="grey85", expand=False))
    console.print()


@app.command(name="create")
def create_person(
    first_name: str | None = typer.Option(None, "--first-name", help="First name"),
    last_name: str | None = typer.Option(None, "--last-name", help="Last name"),
    email: str | None = typer.Option(None, "--email", help="Work email address"),
    mobile_phone: str | None = typer.Option(None, "--phone", help="Mobile phone number"),
    employment_start: str | None = typer.Option(None, "--start-date", help="Employment start date (YYYY-MM-DD)"),
) -> None:
    """Create a new employee record. Prompts for missing required fields."""
    from ..api.errors import APIError
    if not is_json_mode():
        console.print(f"\n[bold {PRIMARY}]Create Employee[/bold {PRIMARY}]\n")

    if not first_name:
        if is_json_mode():
            require_arg(None, "first-name")
        first_name = typer.prompt(" First name")
    if not last_name:
        if is_json_mode():
            require_arg(None, "last-name")
        last_name = typer.prompt(" Last name")
    if not email:
        if is_json_mode():
            require_arg(None, "email")
        email = typer.prompt(" Work email")
    if employment_start:
        employment_start = validate_date(employment_start, "%Y-%m-%d")
    else:
        employment_start = prompt_date("Employment start date")

    try:
        with recoverable_api_call(f"Creating employee {first_name} {last_name}..."):
            data = svc.create_person(
                first_name=first_name, last_name=last_name,
                email=email, employment_start=employment_start,
                mobile_phone=mobile_phone,
            )
            if is_json_mode():
                json_output(data)
                return
            new_id = data.get("id", "—")
            print_success(f"Employee created! ID: [cyan]{new_id}[/cyan]")
    except APIError as exc:
        status = getattr(exc, "status_code", None)
        if status in (409, 400):
            msg = getattr(exc, "message", "").lower()
            if "email" in msg or "duplicate" in msg or status == 409:
                console.print(
                    f"\n  [bold yellow]Tip:[/bold yellow] An employee with the email "
                    f"[bold]{email}[/bold] may already exist.\n"
                )
                from rich.prompt import Prompt
                choice = Prompt.ask(
                    " [bold]How would you like to proceed?[/bold]\n"
                    " [1] Search for existing employee\n"
                    " [2] Try a different email\n"
                    " [3] Abort",
                    choices=["1", "2", "3"],
                    default="1"
                )
                if choice == "1":
                    list_people(search=email)
                    return
                elif choice == "2":
                    create_person(
                        first_name=first_name, last_name=last_name, email=None, 
                        mobile_phone=mobile_phone, employment_start=employment_start
                    )
                    return
                else:
                    return
        raise typer.Exit(exc.exit_code if hasattr(exc, "exit_code") else 1)


@app.command(name="bulk-view")
def bulk_view_people(
    person_ids: str = typer.Argument(..., help="Comma-separated person IDs to view"),
) -> None:
    """View multiple employees at once. Pass comma-separated IDs."""
    ids = [i.strip() for i in person_ids.split(",") if i.strip()]
    if not ids:
        print_error("No valid IDs provided.")
        raise typer.Exit(1)

    with api_call(f"Fetching {len(ids)} employee(s)..."):
        client = KolayClient()
        response = client.post("v2/person/bulk-view", data={"ids": ids})

        data = response.get("data", [])
        items = data if isinstance(data, list) else data.get("items", [])

        if is_json_mode():
            json_output(items)
            return

        if not items:
            print_empty("employees", hint="Check the IDs and try again.")
            return

        console.print(f"\n[bold {PRIMARY}]Bulk Employees View[/bold {PRIMARY}]\n")
        table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
        table.add_column("Name", style="bold white", min_width=22)
        table.add_column("Email", style="grey85")
        table.add_column("Status", justify="center")
        table.add_column("Short ID", style="grey62")

        for p in items:
            name = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() or p.get("name", "—")
            email = p.get("workEmail") or "—"
            table.add_row(name, email, display_status(p.get("status", "")), short_id(str(p.get("id", ""))))

        console.print(table)
        console.print()


@app.command(name="fields")
def show_available_fields() -> None:
    """Show all dictionary fields/tokens available for person updates."""
    with api_call("Fetching available data fields..."):
        data = svc.available_fields()

    if is_json_mode():
        json_output(data)
        return

    if not data:
        print_empty("data fields")
        return

    table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
    table.add_column("#", style="grey62", justify="right", width=4)
    table.add_column("Token", style="bold white", no_wrap=True)
    table.add_column("Label", style="grey85")
    table.add_column("Type", style="grey62")
    table.add_column("Required", justify="center")

    for i, field in enumerate(data, 1):
        token = field.get("token") or field.get("fieldToken") or "—"
        field_label = field.get("label") or field.get("name") or "—"
        req = "[red]Yes[/red]" if field.get("required") else "[grey62]No[/grey62]"
        table.add_row(str(i), token, field_label, field.get("type", "—"), req)

    console.print(f"\n[bold {PRIMARY}]Available Custom Fields[/bold {PRIMARY}]\n")
    console.print(table)
    console.print()


@app.command(name="rehire")
def rehire_person(
    person_id: str | None = typer.Argument(None, help="ID of the person to rehire"),
    start_date: str | None = typer.Option(None, "--start-date", help="New start date (YYYY-MM-DD)"),
) -> None:
    """Rehire a previously terminated employee."""
    from ..api.errors import APIError
    if not person_id:
        person_id = pick_person(status="inactive")

    if start_date:
        start_date = validate_date(start_date)
    else:
        from datetime import datetime
        start_date = prompt_date("New employment start date", default=datetime.now().strftime("%Y-%m-%d"))

    try:
        with recoverable_api_call("Processing rehire..."):
            result = svc.rehire_person(person_id, start_date=start_date)
        if is_json_mode():
            json_output(result)
            return
        print_success("Employee rehired successfully.")
    except APIError as exc:
        msg = getattr(exc, "message", "").lower()
        if "active" in msg or "aktif" in msg or "already" in msg:
            console.print(
                "\n  [bold yellow]Tip:[/bold yellow] This employee may already be active.\n"
                f" Run [bold]kolay person view {person_id}[/bold] to check their current status.\n"
            )
        else:
            console.print(
                "\n  [bold yellow]Tip:[/bold yellow] Check that this employee is actually "
                "in a terminated state before rehiring.\n"
                f" Run [bold]kolay person view {person_id}[/bold] to inspect their profile.\n"
            )
        raise typer.Exit(exc.exit_code if hasattr(exc, "exit_code") else 1)


@app.command(name="list-files")
def list_person_files(person_id: str | None = typer.Argument(None, help="ID of the person")) -> None:
    """List all documents attached to an employee profile."""
    if not person_id:
        person_id = pick_person()

    with api_call("Fetching employee files..."):
        data = svc.list_files(person_id)

    if is_json_mode():
        json_output(data)
        return

    if not data:
        print_empty("files")
        return

    table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
    table.add_column("#", style="grey62", justify="right", width=4)
    table.add_column("Name", style="bold white", min_width=22)
    table.add_column("Folder", style="grey85")
    table.add_column("Short ID", style="grey62")

    for i, f in enumerate(data, 1):
        name = f.get("name") or "—"
        folder = f.get("folderName") or "—"
        table.add_row(str(i), name, folder, short_id(str(f.get("id", ""))))

    console.print(f"\n[bold {PRIMARY}]Employee Files[/bold {PRIMARY}]\n")
    console.print(table)
    console.print()


@app.command(name="delete-file")
def delete_person_file(file_id: str | None = typer.Argument(None, help="ID of the file to delete")) -> None:
    """Delete a document from an employee profile."""
    if not file_id:
        file_id = pick_person_file()

    # 3.1: Resolve filename so confirm shows a human-readable label, not a UUID
    file_label = f"file …{file_id[-8:]}" if len(file_id) > 8 else file_id
    folder_label = ""
    # The file-view endpoint isn't documented; we infer details from list if available
    # pick_person_file already knows the person — but we don't have person_id here.
    # Best effort: use the id itself as label in the confirmation.

    confirm_destructive_action(
        action=f"Delete {file_label}",
        details=[
            ("File ID", f"…{file_id[-8:]}" if len(file_id) > 8 else file_id),
        ],
        warning="The file will be permanently removed from the employee profile.",
    )

    with api_call("Deleting file..."):
        result = svc.delete_file(file_id)
    if is_json_mode():
        json_output(result)
        return
    print_success("File deleted.")
    print_irreversible_warning()


@app.command(name="delete-folder")
def delete_person_folder(folder_id: str | None = typer.Argument(None, help="ID of the folder to delete")) -> None:
    """Delete a folder and all documents inside it from an employee profile."""
    if not folder_id:
        folder_id = pick_person_file()

    confirm_destructive_action(
        action=f"Delete folder …{folder_id[-8:]}" if len(folder_id) > 8 else f"Delete folder {folder_id}",
        details=[
            ("Folder ID", f"…{folder_id[-8:]}" if len(folder_id) > 8 else folder_id),
        ],
        warning="ALL documents inside this folder will be permanently deleted.",
    )

    with api_call("Deleting folder..."):
        result = svc.delete_folder(folder_id)
    if is_json_mode():
        json_output(result)
        return
    print_success("Folder deleted.")
    print_irreversible_warning()


@app.command(name="upload-file")
def upload_file(
    person_id: str | None = typer.Option(None, "--person-id", "-p", help="ID of the person"),
    file_path: str = typer.Option(..., "--file", "-f", help="Path to the file to upload"),
    folder_name: str | None = typer.Option(None, "--folder", help="Target folder name (optional)"),
) -> None:
    """Upload a local document to an employee profile."""
    if not os.path.isfile(file_path):
        print_error(f"File not found: {file_path}")
        raise typer.Exit(1)

    if not person_id:
        person_id = pick_person()

    try:
        client = KolayClient()
        with open(file_path, "rb") as fh:
            files = {"file": (os.path.basename(file_path), fh)}
            form_data = {"personId": safe_id(person_id)}
            if folder_name:
                form_data["folderName"] = folder_name

            # Use the underlying session; pop Content-Type as requests adds the multipart boundary
            session = client.session
            headers = dict(session.headers)
            headers.pop("Content-Type", None)

            if not is_json_mode():
                print_fetching(f"Uploading {os.path.basename(file_path)}...")
            
            resp = session.post(f"{client.base_url}/v2/person/upload-file", data=form_data, files=files, headers=headers, timeout=60)
            resp.raise_for_status()
            result = resp.json()

        if is_json_mode():
            json_output(result)
        else:
            print_success(f"File '{os.path.basename(file_path)}' uploaded successfully.")

    except Exception as e:
        status = 500
        msg = str(e)
        import requests
        if isinstance(e, requests.HTTPError):
            status = e.response.status_code if e.response is not None else 500
            try:
                msg = e.response.json().get("message") or msg
            except Exception:
                pass

        if is_json_mode():
            json_error(msg, status=status, exit_code=1)
        else:
            print_error(msg)
        raise typer.Exit(1)


# ── Person Training Management ────────────────────────────────────────────────

@app.command(name="list-trainings")
def list_person_trainings(person_id: str | None = typer.Argument(None, help="ID of the person")) -> None:
    """List all training assignments for an employee."""
    if not person_id:
        person_id = pick_person()

    with api_call("Fetching training assignments..."):
        data = svc.list_trainings(person_id)

    if is_json_mode():
        json_output(data)
        return

    if not data:
        print_empty("training assignments")
        return

    table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
    table.add_column("#", style="grey62", justify="right", width=4)
    table.add_column("Training", style="bold white", min_width=22)
    table.add_column("Status", justify="center")
    table.add_column("Start", style="grey62")
    table.add_column("End", style="grey62")
    table.add_column("Short ID", style="grey62")

    for i, pt in enumerate(data, 1):
        t = pt.get("training", {})
        tname = t.get("name", "—") if isinstance(t, dict) else str(t)
        st = display_status(str(pt.get("status", "")))
        table.add_row(
            str(i), tname, st,
            fmt_datetime(pt.get("startDate")),
            fmt_datetime(pt.get("endDate")),
            short_id(str(pt.get("id", "")))
        )

    console.print(f"\n[bold {PRIMARY}]Training Assignments[/bold {PRIMARY}]\n")
    console.print(table)
    console.print()


@app.command(name="assign-training")
def assign_training(
    person_id: str | None = typer.Option(None, "--person-id", "-p", help="ID of the person"),
    training_id: str | None = typer.Option(None, "--training-id", "-t", help="ID of the training to assign"),
    start_date: str | None = typer.Option(None, "--start", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
    status: str = typer.Option("waiting", "--status", help="Status: waiting, approved"),
) -> None:
    """Assign a training from the catalogue to an employee."""
    if not person_id:
        person_id = pick_person()
    if not training_id:
        training_id = pick_training()

    with api_call("Assigning training..."):
        svc.assign_training(
            person_id=person_id, training_id=training_id,
            status=status, start_date=start_date, end_date=end_date,
        )
        print_success("Training assigned successfully.")


@app.command(name="update-training")
def update_person_training(
    person_training_id: str | None = typer.Argument(None, help="Assignment ID to update"),
    status: str | None = typer.Option(None, "--status", help="New status"),
    start_date: str | None = typer.Option(None, "--start", help="New start date"),
    end_date: str | None = typer.Option(None, "--end", help="New end date"),
) -> None:
    """Update an existing training assignment."""
    if not person_training_id:
        person_training_id = pick_person_training()

    if not any([status, start_date, end_date]):
        print_error("No fields to update.", hint="Use --status, --start, or --end.")
        return

    with api_call("Updating assignment..."):
        svc.update_training(
            person_training_id,
            status=status, start_date=start_date, end_date=end_date,
        )
        print_success("Assignment updated.")


@app.command(name="delete-training")
def delete_person_training(
    person_training_id: str | None = typer.Argument(None, help="Assignment ID to delete"),
) -> None:
    """Permanently delete a training assignment."""
    if not person_training_id:
        person_training_id = pick_person_training()

    if not is_yes_mode():
        typer.confirm(f" Delete assignment {person_training_id}?", abort=True)

    with api_call("Deleting assignment..."):
        svc.delete_training(person_training_id)
        print_success("Assignment deleted.")
