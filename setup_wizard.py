"""Standalone setup wizard for the Kolay İK MCP server.

Run directly:  python setup_wizard.py
Or as built:   ./dist/kolay-setup
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is importable when running from source.
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
_src_dir = _project_root / "src"
if _src_dir.is_dir() and str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.constants import APP_NAME, SERVER_NAME, DISCLAIMER, TOKEN_HELP
from kolay_cli.security import store_token
from kolay_cli.services.mcp_registry import get_strategies, install_mcp_server

_PRIMARY = "#376BFB"
_SUCCESS = "#57CC99"
_ERROR = "#E62729"

console = Console(highlight=False)


def _resolve_command() -> tuple[str, list[str]]:
    """Detect whether we're running from PyInstaller or source.

    PyInstaller sets sys.frozen. When frozen, the executable itself
    is the MCP server command. Otherwise, use python -m.
    """
    if getattr(sys, "frozen", False):
        return sys.executable, ["mcp", "serve"]
    return sys.executable, ["-m", "kolay_cli.mcp_server"]


def _tilde(path: str) -> str:
    return path.replace(str(Path.home()), "~")


def step_disclaimer() -> bool:
    """Print disclaimer. Return True if the user accepts."""
    console.print()
    console.print(
        Panel(
            f"[bold {_PRIMARY}]{APP_NAME}[/bold {_PRIMARY}]\n\n"
            f"[bold]Alpha Disclaimer[/bold]\n\n"
            f"{DISCLAIMER}",
            border_style=_PRIMARY,
            expand=False,
            padding=(1, 3),
        )
    )
    console.print()
    answer = console.input(f"  [{_PRIMARY}]Accept and continue? (Y/n):[/{_PRIMARY}] ").strip().lower()
    return answer in ("", "y", "yes")


def step_token() -> str | None:
    """Prompt for API token with masked input. Return token or None."""
    console.print()
    console.print(f"  [bold {_PRIMARY}]Step 1[/bold {_PRIMARY}]  API Token\n")
    console.print(f"  [grey62]{TOKEN_HELP}[/grey62]\n")

    import getpass
    try:
        token = getpass.getpass("  Kolay API token: ")
    except (EOFError, KeyboardInterrupt):
        console.print("\n  [grey62]Cancelled.[/grey62]")
        return None

    if not token.strip():
        console.print(f"  [{_ERROR}]Token cannot be empty.[/{_ERROR}]")
        return None

    return token.strip()


def step_store_token(token: str) -> bool:
    """Store token in OS keychain. Return True on success."""
    console.print()
    console.print(f"  [bold {_PRIMARY}]Step 2[/bold {_PRIMARY}]  Storing token\n")
    saved = store_token(token)
    if saved:
        console.print(f"  [bold {_SUCCESS}]✔[/bold {_SUCCESS}]  Token saved to OS Keychain.\n")
    else:
        console.print(f"  [grey62]✔ Token saved to config file (keychain unavailable).[/grey62]\n")
    return saved


def step_select_clients() -> list[str]:
    """Show numbered client list. Return selected strategy names."""
    console.print()
    console.print(f"  [bold {_PRIMARY}]Step 3[/bold {_PRIMARY}]  Install MCP server\n")

    strategies = get_strategies()

    table = Table(
        header_style=f"bold {_PRIMARY}",
        box=None, show_edge=False, padding=(0, 2),
    )
    table.add_column("#", style="grey62", justify="right", width=3)
    table.add_column("Client", style="bold white", min_width=20)
    table.add_column("Config path", style="grey62")

    for i, s in enumerate(strategies, 1):
        p = s.get_config_path()
        path_str = _tilde(str(p)) if p else "n/a"
        table.add_row(str(i), s.name, path_str)

    console.print(table)
    console.print()
    console.print(
        f"  [grey62]Comma-separated numbers → [bold white]1,2[/bold white]   "
        f"All → [bold white]a[/bold white]   "
        f"Skip → [bold white]Enter[/bold white][/grey62]"
    )
    console.print()

    raw = console.input(f"  [{_PRIMARY}]Install which client(s)?[/{_PRIMARY}] ").strip().lower()

    if not raw:
        return []
    if raw in ("a", "all", "*"):
        return [s.name for s in strategies]

    selected: list[str] = []
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(strategies):
                selected.append(strategies[idx].name)
            else:
                console.print(f"  [yellow]⚠ {token} is out of range (1–{len(strategies)})[/yellow]")
        elif token:
            console.print(f"  [yellow]⚠ '{token}' is not a valid number[/yellow]")

    return selected


def step_install(selected_names: list[str]) -> None:
    """Install MCP server into selected clients."""
    if not selected_names:
        console.print("  [grey62]No clients selected. Skipped.[/grey62]\n")
        return

    command, args = _resolve_command()
    results = install_mcp_server(SERVER_NAME, command, args, selected=selected_names)

    console.print()
    success_count = 0
    for client_name, success, msg in results:
        if success:
            console.print(f"  [green]✔[/green] [bold]{client_name}[/bold]: Configured.")
            console.print(f"      [grey62]→ {_tilde(msg)}[/grey62]")
            success_count += 1
        else:
            if "Unsupported" in msg or "not determinable" in msg:
                console.print(f"  [grey50]○[/grey50] [grey62]{client_name}[/grey62]: Skipped ({msg})")
            else:
                console.print(f"  [{_ERROR}]✖[/{_ERROR}] [bold]{client_name}[/bold]: {msg}")

    console.print()
    if success_count > 0:
        console.print(f"  [green]✅ {success_count} client(s) configured.[/green] Restart them to activate.\n")


def main() -> int:
    """Run the full setup wizard. Return exit code."""
    if not step_disclaimer():
        console.print("\n  [grey62]Declined. Exiting.[/grey62]\n")
        return 1

    token = step_token()
    if not token:
        return 2

    step_store_token(token)

    selected = step_select_clients()
    step_install(selected)

    console.print(
        Panel(
            f"[bold {_SUCCESS}]Setup complete.[/bold {_SUCCESS}]\n\n"
            "Try these commands:\n\n"
            f"  [bold]kolay person list[/bold]     [grey62]List employees[/grey62]\n"
            f"  [bold]kolay mcp serve[/bold]       [grey62]Start MCP server[/grey62]\n"
            f"  [bold]kolay doctor[/bold]           [grey62]Verify installation[/grey62]",
            border_style=_SUCCESS,
            expand=False,
            padding=(1, 3),
        )
    )
    console.print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
