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
    console, short_id, display_status, fmt_val, fmt_num, label,
    print_error, print_success, print_fetching, print_empty, kv_table,
    pick_person, pick_training, pick_person_training,
    api_call, no_command_help, PRIMARY,
    is_json_mode, is_yes_mode, json_output, json_error, require_arg, resolve_row,
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

    title = f"👥 {status.title()} Employees"
    if search:
        title += f" matching '{search}'"
    
    console.print(f"\n[bold {PRIMARY}]{title}[/bold {PRIMARY}] [grey62]({len(items)}/{total})[/grey62]\n")
    
    table = Table(header_style=f"bold {PRIMARY}", border_style=PRIMARY, box=None, show_edge=False)
    table.add_column("#", style="grey62", justify="right", width=4)
    table.add_column("Name", style="bold white", min_width=22)
    table.add_column("Email", style="grey85")
    table.add_column("Phone", style="grey62")
    table.add_column("Short ID", style="grey62")

    for i, person in enumerate(items, 1):
        name = f"{person.get('firstName', '')} {person.get('lastName', '')}".strip() or person.get("name", "—")
        email = person.get("workEmail") or person.get("email") or "—"
        phone = person.get("mobilePhone") or "—"
        table.add_row(
            str(i + (page - 1) * limit),
            name, email, phone,
            short_id(str(person.get("id", "")))
        )
    
    console.print(table)
    console.print()


def _resolve_person_id(value: str, *, status: str = "active", limit: int = 50) -> str:
    """Resolve a row-number shorthand (e.g. '1') to a real person UUID."""
    if not value.isdigit():
        return value
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

    console.print(f"\n[bold {PRIMARY}]👤 Employee Profile[/bold {PRIMARY}] [bold white]{fname} {lname}[/bold white]")
    console.print(f"  {display_status(st)}  [grey62]{email}[/grey62]\n")

    tbl = kv_table(data, exclude=["id", "firstName", "lastName", "status", "workEmail", "email", "units"])
    console.print(Panel(tbl, border_style=PRIMARY, expand=False))
    
    # Display Unit Details if available
    units = data.get("units", [])
    if units:
        console.print("\n[bold magenta]🏢 Organisational Units[/bold magenta]")
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

    console.print("\n[bold {PRIMARY}]🏖️ Leave Balances[/bold {PRIMARY}]\n")
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
    require_arg(person_id, "person-id")
    if not person_id:
        person_id = pick_person()

    if not termination_date:
        if is_json_mode():
            require_arg(None, "termination-date")
        from datetime import datetime
        default_date = datetime.now().strftime("%Y-%m-%d")
        termination_date = typer.prompt("  Termination date", default=default_date)

    if not reason:
        if is_json_mode():
            require_arg(None, "reason")
        console.print("\n[bold white]  Termination reasons:[/bold white]")
        for code, desc in svc.REASON_CODES.items():
            console.print(f"  [cyan]{code}[/cyan] : {desc}")
        reason = typer.prompt("\n  Enter reason code", type=str)

    with api_call("Processing termination..."):
        result = svc.terminate_person(person_id, termination_date=termination_date, reason_code=reason)

    if is_json_mode():
        json_output(result)
    else:
        print_success("Employee terminated successfully.")


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

    fname = data.get("firstName", "")
    lname = data.get("lastName", "")
    
    console.print(f"\n[bold {PRIMARY}]📄 Employee Summary[/bold {PRIMARY}] [bold white]{fname} {lname}[/bold white]\n")
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
    console.print("\n[bold {PRIMARY}]👤 Create Employee[/bold {PRIMARY}]\n")
    if not first_name:
        first_name = typer.prompt("  First name")
    if not last_name:
        last_name = typer.prompt("  Last name")
    if not email:
        email = typer.prompt("  Work email")
    if not employment_start:
        employment_start = typer.prompt("  Employment start date (YYYY-MM-DD)")

    with api_call(f"Creating employee {first_name} {last_name}..."):
        data = svc.create_person(
            first_name=first_name, last_name=last_name,
            email=email, employment_start=employment_start,
            mobile_phone=mobile_phone,
        )
        new_id = data.get("id", "—")
        print_success(f"Employee created! ID: [cyan]{new_id}[/cyan]")


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

        if not items:
            print_empty("employees", hint="Check the IDs and try again.")
            return

        console.print("\n[bold {PRIMARY}]👥 Bulk Employees View[/bold {PRIMARY}]\n")
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

    console.print("\n[bold {PRIMARY}]📋 Available Custom Fields[/bold {PRIMARY}]\n")
    console.print(table)
    console.print()


@app.command(name="rehire")
def rehire_person(
    person_id: str | None = typer.Argument(None, help="ID of the person to rehire"),
    start_date: str | None = typer.Option(None, "--start-date", help="New start date (YYYY-MM-DD)"),
) -> None:
    """Rehire a previously terminated employee."""
    if not person_id:
        person_id = pick_person()

    if not start_date:
        from datetime import datetime
        start_date = typer.prompt("  New employment start date (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))

    with api_call("Processing rehire..."):
        svc.rehire_person(person_id, start_date=start_date)
        print_success("Employee rehired successfully.")


@app.command(name="list-files")
def list_person_files(person_id: str | None = typer.Argument(None, help="ID of the person")) -> None:
    """List all documents attached to an employee profile."""
    if not person_id:
        person_id = pick_person()

    with api_call("Fetching employee files..."):
        data = svc.list_files(person_id)

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

    console.print(f"\n[bold {PRIMARY}]📁 Employee Files[/bold {PRIMARY}]\n")
    console.print(table)
    console.print()


@app.command(name="delete-file")
def delete_person_file(file_id: str | None = typer.Argument(None, help="ID of the file to delete")) -> None:
    """Delete a document from an employee profile."""
    if not file_id:
        console.print("[grey62]  Tip: run 'kolay person list-files' to find file IDs.[/grey62]")
        file_id = typer.prompt("  File ID")
    
    if not is_yes_mode():
        typer.confirm(f"  Delete file {file_id}?", abort=True)

    with api_call("Deleting file..."):
        svc.delete_file(file_id)
        print_success("File deleted.")


@app.command(name="delete-folder")
def delete_person_folder(folder_id: str | None = typer.Argument(None, help="ID of the folder to delete")) -> None:
    """Delete a folder and all documents inside it from an employee profile."""
    if not folder_id:
        console.print("[grey62]  Tip: run 'kolay person list-files' to find folder IDs.[/grey62]")
        folder_id = typer.prompt("  Folder ID")
    
    if not is_yes_mode():
        typer.confirm(f"  Delete folder {folder_id}? All contents will be lost.", abort=True)

    with api_call("Deleting folder..."):
        svc.delete_folder(folder_id)
        print_success("Folder deleted.")


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
        url = f"{client.base_url}/v2/person/upload-file"
        
        with open(file_path, "rb") as fh:
            files = {"file": (os.path.basename(file_path), fh)}
            form_data = {"personId": safe_id(person_id)}
            if folder_name:
                form_data["folderName"] = folder_name

            # Use session for auth but remove Content-Type for multipart
            session = client.session
            headers = dict(session.headers)
            headers.pop("Content-Type", None)

            print_fetching(f"Uploading {os.path.basename(file_path)}...")
            resp = session.post(url, data=form_data, files=files, headers=headers, timeout=60)
            resp.raise_for_status()

        print_success(f"File '{os.path.basename(file_path)}' uploaded successfully.")

    except Exception as e:
        import requests
        if isinstance(e, requests.HTTPError):
            status = e.response.status_code if e.response is not None else None
            msg = f"Upload failed: HTTP {status}"
            if is_json_mode():
                json_error(msg, status=status, exit_code=1)
            else:
                print_error(msg)
            raise typer.Exit(1)
        if is_json_mode():
            json_error(str(e), exit_code=1)
        else:
            print_error(str(e))
        raise typer.Exit(1)


# ── Person Training Management ────────────────────────────────────────────────

@app.command(name="list-trainings")
def list_person_trainings(person_id: str | None = typer.Argument(None, help="ID of the person")) -> None:
    """List all training assignments for an employee."""
    if not person_id:
        person_id = pick_person()

    with api_call("Fetching training assignments..."):
        data = svc.list_trainings(person_id)

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
            (pt.get("startDate") or "—")[:10],
            (pt.get("endDate") or "—")[:10],
            short_id(str(pt.get("id", "")))
        )

    console.print(f"\n[bold {PRIMARY}]🎓 Training Assignments[/bold {PRIMARY}]\n")
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
        typer.confirm(f"  Delete assignment {person_training_id}?", abort=True)

    with api_call("Deleting assignment..."):
        svc.delete_training(person_training_id)
        print_success("Assignment deleted.")
