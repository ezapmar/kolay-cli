from __future__ import annotations
import typer
from rich.panel import Panel

from ..config import get_base_url
from ..security import (
    store_token, delete_token, resolve_token, resolve_token_with_source,
    validate_token, _keyring_available,
)
from ..api import KolayClient, APIError
from ..ui import (
    console, print_error, kv_table, api_call, no_command_help, PRIMARY, SUCCESS, ERROR,
    is_json_mode, json_output,
)

app = typer.Typer(help="Authenticate and manage your Kolay API session.")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


def _perform_login(token: str, _console: "Console | None" = None) -> None:  # type: ignore[name-defined]
    """Store the token and verify it against the API, then print the result.

    Shared by ``kolay auth login`` (interactive) and ``kolay setup`` (wizard)
    so the store-verify-display flow is defined in a single place.

    Args:
        token: The raw bearer token to store and verify.
        _console: Rich Console to use for output (defaults to the module console).
    """
    from rich.console import Console as _Console
    _con = _console or console

    saved_to_keyring = store_token(token)
    storage_label = "OS Keychain 🔐" if saved_to_keyring else "config file (keyring unavailable)"

    try:
        with api_call("Verifying token..."):
            client = KolayClient(token=token)
            response = client.get("v2/profile/me")
        data = response.get("data", {})
        name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
        if is_json_mode():
            json_output({
                "status": "authenticated",
                "name": name,
                "token_storage": "keyring" if saved_to_keyring else "config_file",
            })
            return
        _con.print(
            Panel(
                f"[{SUCCESS}]Authenticated successfully![/{SUCCESS}]\n\n"
                f"[bold white]{name}[/bold white]\n\n"
                f"[grey62]Token saved to: {storage_label}[/grey62]",
                title=f"[{SUCCESS}]✔ Logged In[/{SUCCESS}]",
                border_style=SUCCESS, expand=False, padding=(1, 2)
            )
        )
        _con.print(f"  [grey62]💡 Run [bold]kolay doctor[/bold] to verify your full setup.[/grey62]\n")
    except SystemExit:
        if is_json_mode():
            json_output({"status": "error", "message": "Token saved but verification failed."})
            return
        _con.print(
            f"[grey62]  Token saved to {storage_label}, but verification failed.\n"
            f"  Run [bold]kolay config validate[/bold] to retry.[/grey62]\n"
        )


@app.command()
def login(token: str = typer.Option(..., prompt="Kolay API token", hide_input=True)) -> None:
    """Save your Kolay API token securely and verify it against the API."""
    _perform_login(token)



@app.command()
def logout() -> None:
    """Remove your stored API token from the OS Keychain and config file."""
    from ..security import _remove_token_from_config_file

    removed_keyring = delete_token()
    # Belt-and-suspenders: also strip from any config file
    _remove_token_from_config_file()
    removed_file = True  # _remove_token_from_config_file() is fire-and-forget

    if is_json_mode():
        json_output({
            "status": "logged_out",
            "keyring_cleared": removed_keyring,
            "config_file_cleared": removed_file,
        })
        return

    if removed_keyring or removed_file:
        console.print(f"\n[{SUCCESS}]●[/{SUCCESS}] Logged out successfully.\n")
        if removed_keyring:
            console.print(f"  [grey62]✔ Removed from OS Keychain[/grey62]")
        console.print(f"  [grey62]✔ Config file cleaned[/grey62]")
        console.print()
    else:
        console.print(f"\n[grey62]  No stored token found — already logged out.[/grey62]\n")



@app.command()
def status() -> None:
    """Check if you are currently logged in and show your profile."""
    token, token_source = resolve_token_with_source()
    if not token:
        if is_json_mode():
            json_output({"authenticated": False, "message": "No API token set."})
            return
        print_error(
            "You are not logged in.",
            hint="Run [bold]kolay auth login[/bold] to set your API token.",
        )
        return

    # Validate locally first
    validation = validate_token(token)
    if not validation:
        if is_json_mode():
            json_output({"authenticated": False, "message": validation.reason})
            return
        print_error(validation.reason, hint="Run [bold]kolay auth login[/bold] to refresh.")
        return

    try:
        with api_call("Checking token..."):
            client = KolayClient(token=token)
            response = client.get("v2/profile/me")
        data = response.get("data", {})
        name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
        email = data.get("workEmail") or data.get("email") or ""
        if is_json_mode():
            json_output({"authenticated": True, "name": name, "email": email, "token_source": token_source})
            return
        console.print(
            f"\n[{SUCCESS}]●[/{SUCCESS}] Logged in as [bold white]{name}[/bold white]  "
            f"[grey62]{email}[/grey62]  [grey50](token: {token_source})[/grey50]\n"
        )
    except SystemExit:
        if is_json_mode():
            json_output({"authenticated": False, "message": "Token exists but API verification failed."})
            return
        console.print(
            f"\n[{ERROR}]●[/{ERROR}] Token exists but API verification failed.\n"
            f"  [grey62]Run [bold]kolay auth login[/bold] to refresh.[/grey62]\n"
        )


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
