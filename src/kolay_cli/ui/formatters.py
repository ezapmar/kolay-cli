"""UI formatters for kolay-cli."""
from __future__ import annotations
import sys
import time
from contextlib import contextmanager
from typing import Any, Generator

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .constants import (
    STATUS_STYLES, FIELD_LABELS,
    PRIMARY, ACCENT, SUCCESS, WARNING, ERROR,
)


console = Console(highlight=False)




@contextmanager
def spinner(message: str = "Working...") -> Generator[None, None, None]:
    """Show a live Kolay-branded spinner."""
    from .output import is_json_mode
    if is_json_mode():
        yield  # no spinner in JSON mode
    else:
        with console.status(f"[{PRIMARY}]{message}[/{PRIMARY}]", spinner="dots"):
            yield


@contextmanager
def api_call(message: str = "Working...") -> Generator[None, None, None]:
    """Spinner + automatic error handling for API operations."""
    import typer
    from ..api.errors import APIError
    from .output import is_json_mode, json_error

    try:
        with spinner(message):
            yield
    except APIError as exc:
        if is_json_mode():
            json_error(exc.message, status=exc.status_code, hint=exc.hint, exit_code=exc.exit_code)
        else:
            print_api_error(exc)
        raise typer.Exit(exc.exit_code)


@contextmanager
def recoverable_api_call(message: str = "Working...") -> Generator[None, None, None]:
    """Like api_call(), but re-raises APIError for the caller to handle recovery.

    Use this for interactive mutating commands where the user may want to retry
    with different input rather than hitting a dead end.
    """
    from ..api.errors import APIError
    from .output import is_json_mode, json_error

    try:
        with spinner(message):
            yield
    except APIError as exc:
        if is_json_mode():
            json_error(exc.message, status=exc.status_code, hint=exc.hint, exit_code=exc.exit_code)
        # In interactive mode: print the error but let the caller decide
        print_api_error(exc)
        raise


def no_command_help(ctx: "typer.Context") -> None:  # type: ignore[name-defined]
    """Handle command groups invoked with no subcommand."""
    import typer

    if ctx.invoked_subcommand is not None:
        return

    name = ctx.info_name or "this command"
    console.print(
        f"\n[bold {PRIMARY}]kolay {name}[/bold {PRIMARY}] needs a sub-command.\n"
        f"  Try: [bold]kolay {name} --help[/bold]\n"
    )

    # 3-second countdown with a live status indicator
    for secs in (3, 2, 1):
        with console.status(
            f"[{PRIMARY}]Showing help in {secs}…[/{PRIMARY}]",
            spinner="dots",
        ):
            time.sleep(1)

    console.print()
    console.print(ctx.get_help())
    raise typer.Exit(0)




def short_id(full_id: str) -> str:
    """Truncate UUID to last 8 chars."""
    if not full_id or full_id in ("N/A", "—"):
        return "[grey62]—[/grey62]"
    clean = str(full_id)
    return f"[grey62]…{clean[-8:]}[/grey62]" if len(clean) > 8 else f"[grey62]{clean}[/grey62]"


def display_status(status: str) -> str:
    """Styled status badge."""
    if not status:
        return "[grey62]—[/grey62]"
    return STATUS_STYLES.get(str(status).lower(), f"[grey62]{status}[/grey62]")




def fmt_val(val: Any) -> str:
    """Format value for display (handles None, bool, empty)."""
    if val is None or val == "" or val == "N/A":
        return "[grey62]—[/grey62]"
    if isinstance(val, bool):
        return f"[{SUCCESS}]Yes[/{SUCCESS}]" if val else f"[{ERROR}]No[/{ERROR}]"
    return str(val)


def fmt_num(val: Any) -> str:
    """Format numeric value."""
    if val is None:
        return "[grey62]—[/grey62]"
    try:
        f = float(val)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(val)


def label(key: str) -> str:
    """Convert camelCase API key to human label."""
    return FIELD_LABELS.get(key, key.replace("_", " ").title())




_WITTY_STATUS = {401, 403, 429, 500, 502, 503}

# Status-code → border colour (softer tones so it doesn't look like a crash)
_WITTY_BORDER: dict[int, str] = {
    401: WARNING,   # orange — oops, identity issue
    403: WARNING,   # orange — permission, not a crash
    429: ACCENT,    # blue   — slow down, not broken
    500: ERROR,     # red    — actual server problem
    502: ERROR,
    503: ERROR,
}


def print_api_error(exc: "APIError") -> None:  # type: ignore[name-defined]
    """Render error panel for APIError."""
    from .messages import get_scenario

    status = exc.status_code or 0
    scenario = get_scenario(status) if status in _WITTY_STATUS else None

    if scenario:
        headline, body, hint = scenario
        border = _WITTY_BORDER.get(status, WARNING)
        panel_body = f"{body}\n\n[grey85]{hint}[/grey85]"
        console.print()
        console.print(
            Panel(
                panel_body,
                title=f"[bold {border}]{headline}[/bold {border}]",
                border_style=border,
                expand=False,
                padding=(1, 2),
            )
        )
    else:
        print_error(exc.message, hint=exc.hint)


def print_error(msg: str, hint: str | None = None) -> None:
    """Render error panel with recovery hint."""
    # Strip redundant prefixes the API client may have added
    clean = msg
    for prefix in ("API Error: API Error:", "API Error:", "Request failed:"):
        if clean.startswith(prefix):
            clean = clean[len(prefix):].strip()
            break

    body = f"[bold {ERROR}]{clean}[/bold {ERROR}]"
    if hint:
        body += f"\n\n[grey85]{hint}[/grey85]"

    console.print()
    console.print(
        Panel(body, title=f"[{ERROR}]Error[/{ERROR}]", border_style=ERROR, expand=False, padding=(1, 2))
    )


def print_success(msg: str) -> None:
    """Print a clean success confirmation using Kolay Cheer green.

    Args:
        msg: The success message to display.
    """
    from .output import is_json_mode
    if not is_json_mode():
        console.print(f"\n[bold {SUCCESS}]  \u2714[/bold {SUCCESS}] {msg}\n")


def print_fetching(msg: str) -> None:
    """Print a dim loading hint (prefer ``spinner`` or ``api_call`` instead).

    Args:
        msg: The loading message.
    """
    from .output import is_json_mode
    if not is_json_mode():
        console.print(f"[grey62]  {msg}[/grey62]")


def print_empty(entity: str, hint: str | None = None) -> None:
    """Print a context-aware empty-state message.

    Args:
        entity: The name of the entity (e.g. ``employees``).
        hint: An optional hint for the user.
    """
    from .output import is_json_mode
    if not is_json_mode():
        console.print(f"\n[grey62]  No {entity} found.[/grey62]")
        if hint:
            console.print(f"  [grey62]\u2192 {hint}[/grey62]")
        console.print()




def kv_table(data: dict[str, Any], exclude: list[str] | None = None) -> Table:
    """Build key-value detail table."""
    exclude = exclude or []
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0), expand=False)
    table.add_column("Key", style="grey85", no_wrap=True, min_width=16)
    table.add_column("Value")
    for k, v in data.items():
        if k in exclude or isinstance(v, (dict, list)):
            continue
        table.add_row(label(k), fmt_val(v))
    return table
