"""
kolay config — View, set, and validate CLI configuration.
"""
from __future__ import annotations
import typer
from rich.panel import Panel
from rich.table import Table

from ..config import Config, CONFIG_FILE_YAML, CONFIG_FILE_JSON, get_api_token
from ..ui import (
    console, print_success, print_error, api_call, no_command_help, PRIMARY, SUCCESS, ERROR,
    is_json_mode, json_output,
)

app = typer.Typer(help="View and manage your Kolay CLI configuration.")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    no_command_help(ctx)


@app.command(name="show")
def config_show() -> None:
    """Show the active configuration (sources and current values)."""
    import os
    cfg = Config()

    token_raw = cfg.api_token
    token_source = "env" if os.getenv("KOLAY_API_TOKEN") else "file"
    token_display = f"\u2026{token_raw[-8:]}" if token_raw and len(token_raw) > 8 else (token_raw or "")

    yaml_exists = CONFIG_FILE_YAML.exists()
    json_exists = CONFIG_FILE_JSON.exists()
    config_file = str(CONFIG_FILE_YAML if yaml_exists else CONFIG_FILE_JSON if json_exists else CONFIG_FILE_YAML)

    if is_json_mode():
        json_output({
            "token_set": bool(token_raw),
            "token_source": token_source,
            "base_url": cfg.base_url,
            "config_file": config_file,
        })
        return

    tbl = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    tbl.add_column("Key", style="grey85", min_width=18, no_wrap=True)
    tbl.add_column("Value")

    tbl.add_row("API Token", f"[grey62]{token_display}[/grey62]  [grey62]({token_source})[/grey62]")
    tbl.add_row("Base URL", cfg.base_url)
    tbl.add_row("Config file", config_file)

    console.print()
    console.print(Panel(tbl, title=f"[{PRIMARY}]Kolay CLI Configuration[/{PRIMARY}]",
                        border_style=PRIMARY, expand=False, padding=(1, 2)))
    console.print()

    if not token_raw:
        console.print(f" [{ERROR}]No API token set.[/{ERROR}]")
        console.print(f" [grey62]Run [bold]kolay auth login[/bold] to authenticate.[/grey62]\n")


@app.command(name="set")
def config_set(
    key: str = typer.Argument(..., help="Config key (e.g. api_token, base_url)"),
    value: str = typer.Argument(..., help="The value to set"),
) -> None:
    """Set a configuration value and save it to the config file."""
    cfg = Config()
    cfg.set(key, value)
    print_success(f"Set [bold]{key}[/bold] in config file.")


@app.command(name="validate")
def config_validate() -> None:
    """Verify that the stored API token is valid by making a test API call.

    Makes a lightweight call to v2/profile/me and shows the authenticated user.
    """
    from ..api import KolayClient, APIError

    token = get_api_token()
    if not token:
        print_error(
            "No API token found.",
            hint="Run [bold]kolay auth login[/bold] to set one.",
        )
        raise typer.Exit(1)

    with api_call("Validating token..."):
        client = KolayClient(token=token)
        response = client.get("v2/profile/me")

    data = response.get("data", {})
    if is_json_mode():
        json_output({
            "valid": True,
            "name": f"{data.get('firstName', '')} {data.get('lastName', '')}".strip(),
            "email": data.get("workEmail") or data.get("email") or "",
        })
        return
    first = data.get("firstName", "")
    last = data.get("lastName", "")
    email = data.get("workEmail") or data.get("email") or "—"

    console.print()
    console.print(
        Panel(
            f"[{SUCCESS}]Token is valid![/{SUCCESS}]\n\n"
            f"[bold white]{first} {last}[/bold white]  [grey62]{email}[/grey62]",
            title=f"[{SUCCESS}]Authenticated[/{SUCCESS}]",
            border_style=SUCCESS,
            expand=False,
            padding=(1, 2),
        )
    )
    console.print()
