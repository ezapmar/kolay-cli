"""Guided setup wizard for kolay-cli."""
from __future__ import annotations

import os
import subprocess
import sys

import typer
from rich.console import Console
from rich.panel import Panel

from ..config import get_api_token

app = typer.Typer(help="Guided first-run setup wizard.")
console = Console(highlight=False)

from ..ui.constants import PRIMARY as _PRIMARY
_SUCCESS = "#57CC99"


@app.callback(invoke_without_command=True)
def setup(ctx: typer.Context) -> None:
    """Interactive setup wizard."""
    from ..ui.output import is_json_mode

    if is_json_mode():
        console.print("[grey62]Setup wizard is interactive — run without --json.[/grey62]")
        raise typer.Exit(2)


    from ..ui.constants import KOLAY_LOGO
    console.print(KOLAY_LOGO)
    console.print(
        Panel(
            f"[bold {_PRIMARY}]Welcome to Kolay CLI[/bold {_PRIMARY}]\n\n"
            "This wizard will get you up and running in under a minute.\n"
            "You'll need your Kolay API token from [bold]app.kolayik.com[/bold].",
            border_style=_PRIMARY,
            expand=False,
            padding=(1, 3),
        )
    )
    console.print()


    token = get_api_token()
    if token:
        console.print(f"  [bold {_SUCCESS}]✔[/bold {_SUCCESS}]  API token already configured.\n")
        reconfigure = typer.confirm("  Reconfigure token?", default=False)
        if not reconfigure:
            console.print()
        else:
            _do_auth()
    else:
        console.print(f"  [bold {_PRIMARY}]Step 1[/bold {_PRIMARY}]  Authenticate\n")
        _do_auth()


    shell = os.environ.get("SHELL", "")
    shell_name = "zsh" if "zsh" in shell else ("bash" if "bash" in shell else None)

    if shell_name:
        console.print(f"  [bold {_PRIMARY}]Step 2[/bold {_PRIMARY}]  Shell completion ({shell_name})\n")
        install_comp = typer.confirm(f"  Install {shell_name} auto-completion?", default=True)
        if install_comp:
            try:
                subprocess.run(
                    [sys.executable, "-m", "kolay_cli.cli", "--install-completion", shell_name],
                    capture_output=True, text=True, check=False,
                )
                console.print(f"  [bold {_SUCCESS}]✔[/bold {_SUCCESS}]  Completion installed. Restart your shell to activate.\n")
            except Exception:
                console.print("  [grey62]  Could not install completion automatically. Run:[/grey62]")
                console.print(f"       [bold]kolay --install-completion {shell_name}[/bold]\n")
        else:
            console.print("  [grey62]  Skipped. You can always run:[/grey62]")
            console.print(f"       [bold]kolay --install-completion {shell_name}[/bold]\n")
    else:
        console.print(f"  [bold {_PRIMARY}]Step 2[/bold {_PRIMARY}]  Shell completion\n")
        console.print(f"  [grey62]  Could not detect your shell. Run manually:[/grey62]")
        console.print(f"       [bold]kolay --install-completion[/bold]\n")


    console.print(f"  [bold {_PRIMARY}]Step 3[/bold {_PRIMARY}]  Verifying installation\n")
    from .doctor import doctor as run_doctor
    run_doctor(ctx)


    console.print(
        Panel(
            f"[bold {_SUCCESS}]You're all set! 🎉[/bold {_SUCCESS}]\n\n"
            "Try these commands to get started:\n\n"
            f"  [bold]kolay person list[/bold]          [grey62]List employees[/grey62]\n"
            f"  [bold]kolay leave list[/bold]           [grey62]View leave records[/grey62]\n"
            f"  [bold]kolay calendar list[/bold]        [grey62]Upcoming events[/grey62]",
            border_style=_SUCCESS,
            expand=False,
            padding=(1, 3),
        )
    )
    console.print()


def _do_auth() -> None:
    """Run authentication login flow."""
    from .auth import _perform_login
    token = typer.prompt("  Kolay API token", hide_input=True)
    _perform_login(token, _console=console)

