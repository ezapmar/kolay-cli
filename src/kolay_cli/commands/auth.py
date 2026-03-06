from __future__ import annotations
import typer
from rich.panel import Panel

from ..config import set_config_value, get_api_token
from ..api import KolayClient, APIError
from ..ui import (
    console, print_error, kv_table, api_call, no_command_help, PRIMARY, SUCCESS, ERROR,
    is_json_mode, json_output,
)

app = typer.Typer(help="Authenticate and manage your Kolay API session.")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


@app.command()
def login(token: str = typer.Option(..., prompt="Kolay API token", hide_input=True)) -> None:
    """Save your Kolay API token and verify it against the API."""
    set_config_value("api_token", token)
    try:
        with api_call("Verifying token..."):
            client = KolayClient(token=token)
            response = client.get("v2/profile/me")
        data = response.get("data", {})
        name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
        if is_json_mode():
            json_output({"status": "authenticated", "name": name})
            return
        console.print(
            Panel(
                f"[{SUCCESS}]Authenticated successfully![/{SUCCESS}]\n\n"
                f"[bold white]{name}[/bold white]",
                title=f"[{SUCCESS}]✔ Logged In[/{SUCCESS}]",
                border_style=SUCCESS, expand=False, padding=(1, 2)
            )
        )
    except SystemExit:
        if is_json_mode():
            json_output({"status": "error", "message": "Token saved but verification failed."})
            return
        console.print(f"[grey62]  Token saved but verification failed. Run [bold]kolay config validate[/bold] to retry.[/grey62]\n")


@app.command()
def status() -> None:
    """Check if you are currently logged in and show your profile."""
    token = get_api_token()
    if not token:
        if is_json_mode():
            json_output({"authenticated": False, "message": "No API token set."})
            return
        print_error(
            "You are not logged in.",
            hint="Run [bold]kolay auth login[/bold] to set your API token.",
        )
        return
    try:
        with api_call("Checking token..."):
            client = KolayClient(token=token)
            response = client.get("v2/profile/me")
        data = response.get("data", {})
        name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
        email = data.get("workEmail") or data.get("email") or ""
        if is_json_mode():
            json_output({"authenticated": True, "name": name, "email": email})
            return
        console.print(f"\n[{SUCCESS}]●[/{SUCCESS}] Logged in as [bold white]{name}[/bold white]  [grey62]{email}[/grey62]\n")
    except SystemExit:
        if is_json_mode():
            json_output({"authenticated": False, "message": "Token exists but API verification failed."})
            return
        console.print(f"\n[{ERROR}]●[/{ERROR}] Token exists but API verification failed.\n  [grey62]Run [bold]kolay auth login[/bold] to refresh.[/grey62]\n")


@app.command()
def me() -> None:
    """Show the full profile of the currently authenticated user."""
    with api_call("Fetching your profile..."):
        client = KolayClient()
        response = client.get("v2/profile/me")

    data = response.get("data", {})
    if is_json_mode():
        json_output(data)
        return
    name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
    console.print(f"\n[bold {PRIMARY}]My Profile[/bold {PRIMARY}]  [bold white]{name}[/bold white]\n")
    console.print(Panel(kv_table(data), border_style=PRIMARY, expand=False))
    console.print()
