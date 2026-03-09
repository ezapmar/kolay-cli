"""UI formatters for kolay-cli."""
from __future__ import annotations
import sys
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
    console.print(ctx.get_help())
    raise typer.Exit(0)


def print_next_steps(steps: list[tuple[str, str]]) -> None:
    """Print a contextual 'what\'s next' hint block after list commands.

    Each step is a (command, description) tuple, e.g.::

        [("kolay person view <#>", "View full profile"),
         ("kolay person list --search name", "Search by name")]

    Automatically skipped in JSON mode.
    """
    from .output import is_json_mode
    if is_json_mode():
        return
    parts = "".join(
        f"  [bold white]{cmd}[/bold white]  [grey50]{desc}[/grey50]\n"
        for cmd, desc in steps
    )
    console.print(f"  [grey50]💡 Next steps:[/grey50]\n{parts}")


def print_pagination_footer(
    *,
    command: str,
    page: int,
    limit: int,
    shown: int,
    total: int,
    extra_flags: str = "",
) -> None:
    """Print a pagination status footer below a list table.

    Renders one of three states:

    * **More pages ahead** — shows current range + next-page command.
    * **Last page / single page with exact match** — shows range, no next hint.
    * **Limit-only mode** (pass ``page=0``) — just shows "Showing N of total"
      with a truncation warning when ``shown == limit < total``.

    Args:
        command:     Full kolay command prefix, e.g. ``"kolay person list"``.
        page:        Current 1-based page number (pass 0 for limit-only mode).
        limit:       Records per page / max records fetched.
        shown:       Number of items actually rendered (after client filtering).
        total:       Total records on the server.
        extra_flags: Additional flags to echo in the next-page hint, e.g.
                     ``"--status waiting"`` so the user's context is preserved.
    """
    from .output import is_json_mode
    if is_json_mode() or shown == 0:
        return

    PRIMARY_ = PRIMARY  # local alias

    if page > 0:
        # ── Paginated mode ───────────────────────────────────────────────────
        first = (page - 1) * limit + 1
        last = first + shown - 1
        total_pages = max(1, (total + limit - 1) // limit)

        range_str = f"{first}–{last} of {total}"
        page_str = f"Page {page} of {total_pages}"

        if page < total_pages:
            next_page = page + 1
            flags = f"--page {next_page}"
            if extra_flags:
                flags = f"{extra_flags} {flags}"
            next_cmd = f"{command} {flags}"
            console.print(
                f"  [grey50]{page_str}  ·  Showing {range_str}  ·  "
                f"Next: [bold white]{next_cmd}[/bold white][/grey50]"
            )
        else:
            # Last page reached
            if total_pages > 1:
                console.print(
                    f"  [grey50]{page_str}  ·  Showing {range_str}  ·  "
                    f"[{PRIMARY_}]All caught up ✓[/{PRIMARY_}][/grey50]"
                )
            else:
                # Single page, show count
                console.print(
                    f"  [grey50]Showing {shown} of {total} records[/grey50]"
                )
    else:
        # ── Limit-only mode (e.g. leave list) ───────────────────────────────
        if shown == limit and total > limit:
            flags = f"--limit {min(limit * 2, total)}"
            if extra_flags:
                flags = f"{extra_flags} {flags}"
            console.print(
                f"  [grey50]Showing {shown} of {total} records  ·  "
                f"More available: [bold white]{command} {flags}[/bold white][/grey50]"
            )
        else:
            console.print(
                f"  [grey50]Showing {shown} of {total} records[/grey50]"
            )
    console.print()


def confirm_destructive_action(
    *,
    action: str,
    details: list[tuple[str, str]],
    warning: str | None = None,
) -> None:
    """Render a warning panel then ask for explicit confirmation.

    Aborts with exit code 1 if the user declines.  Skipped entirely in
    ``--yes`` mode so automated scripts remain non-interactive.

    Args:
        action:  Short imperative description, e.g.
                 ``"Terminate Ahmed Yılmaz"`` or ``"Delete timelog record"``.
        details: Ordered list of ``(label, value)`` rows shown inside the
                 panel, e.g. ``[("Employee", "Ahmed Yılmaz"), ("Date", "2026-03-09")]``.
        warning: Optional extra warning line shown in red below the details,
                 e.g. ``"This will be reported to SGK — legal record."``.
    """
    from .output import is_json_mode, is_yes_mode
    import typer as _typer

    if is_json_mode() or is_yes_mode():
        return

    console.print()
    console.print(f"  [bold red]⚠  {action}[/bold red]")
    for lbl, val in details:
        console.print(f"  [grey62]  {lbl}:[/grey62] [bold white]{val}[/bold white]")
    if warning:
        console.print(f"  [red]  ⚠  {warning}[/red]")
    console.print()

    confirmed = _typer.confirm("  Confirm?", default=False)
    if not confirmed:
        console.print("\n  [grey62]Aborted — no changes made.[/grey62]\n")
        raise _typer.Exit(1)


def print_irreversible_warning() -> None:
    """Print a brief 'cannot be undone' notice after a destructive action.

    Skipped in JSON mode (machine consumers don't need prose warnings).
    """
    from .output import is_json_mode
    if is_json_mode():
        return
    console.print(
        "  [grey50]💡 This action cannot be undone from the CLI. "
        "Contact your Kolay admin if you need to restore.[/grey50]\n"
    )

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

def validate_date(value: str, fmt: str = "%Y-%m-%d") -> str:
    """Validate and normalize a date string. Aborts with code 2 if invalid."""
    from datetime import datetime
    import typer
    from .output import is_json_mode, json_error
    try:
        return datetime.strptime(value.strip(), fmt).strftime(fmt)
    except Exception:
        if is_json_mode():
            json_error(f"Invalid date format. Expected {fmt}", exit_code=2)
        else:
            console.print(f"\n  [bold red]Error:[/bold red] Invalid date '{value}'. Expected format: {fmt}\n")
        raise typer.Exit(2)


def prompt_date(prompt_text: str, default: str | None = None, is_datetime: bool = False) -> str:
    """Interactively prompt for a date, looping until valid.
    
    Adds the (YYYY-MM-DD...) hint automatically.
    """
    from datetime import datetime
    import typer
    fmt = "%Y-%m-%d %H:%M:%S" if is_datetime else "%Y-%m-%d"
    hint = "YYYY-MM-DD HH:MM:SS" if is_datetime else "YYYY-MM-DD"
    while True:
        val = typer.prompt(f"{prompt_text} ({hint})", default=default).strip()
        try:
            return datetime.strptime(val, fmt).strftime(fmt)
        except ValueError:
            console.print(f"  [red]Invalid format. Please use {hint}.[/red]")


def fmt_datetime(dt: str | None, fallback: str = "—") -> str:
    """Format a raw API datetime string (YYYY-MM-DD HH:MM:SS) for display (e.g., '15 Mar 2026')."""
    if not dt or dt == "—":
        return fallback
    from datetime import datetime
    try:
        # Handles both "YYYY-MM-DD HH:MM:SS" and just dates
        if len(dt) > 10:
            return datetime.strptime(dt[:19], "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y  %H:%M")
        return datetime.strptime(dt[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return dt



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
    import re
    if key in FIELD_LABELS:
        return FIELD_LABELS[key]
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", key).replace("_", " ").title()




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
