"""Kolay CLI entry point."""
from __future__ import annotations
import typer
from rich.console import Console

from . import __version__


from .commands import (
    auth, person, leave, transaction, calendar,
    timelog, training, unit, expense, approval, schema,
    doctor, setup, nudge, payroll,
)
from .commands import config as config_cmd  # avoid shadowing built-in
from .commands import mcp as mcp_cmd

from .ui.constants import KOLAY_LOGO, KOLAY_LOGO_COMPACT, PRIMARY
_LOGO = KOLAY_LOGO
_LOGO_COMPACT = KOLAY_LOGO_COMPACT
_PRIMARY = PRIMARY

app = typer.Typer(
    no_args_is_help=False,   # we handle the no-args case ourselves to show the logo
    rich_markup_mode="rich",
)
console = Console(highlight=False)


app.add_typer(auth.app,         name="auth",        rich_help_panel="Authentication")
app.add_typer(config_cmd.app,   name="config",      rich_help_panel="Authentication")
app.add_typer(person.app,       name="person",      rich_help_panel="People")
app.add_typer(leave.app,        name="leave",       rich_help_panel="People")
app.add_typer(timelog.app,      name="timelog",      rich_help_panel="People")
app.add_typer(training.app,     name="training",    rich_help_panel="People")
app.add_typer(transaction.app,  name="transaction", rich_help_panel="Finance")
app.add_typer(expense.app,      name="expense",     rich_help_panel="Finance")
app.add_typer(payroll.app,      name="payroll",     rich_help_panel="Finance")
app.add_typer(approval.app,     name="approval",    rich_help_panel="Workflows")
app.add_typer(calendar.app,     name="calendar",    rich_help_panel="Workflows")
app.add_typer(unit.app,         name="unit",        rich_help_panel="Organisation")
app.add_typer(setup.app,        name="setup",       rich_help_panel="Getting Started")
app.add_typer(doctor.app,       name="doctor",      rich_help_panel="Getting Started")
app.add_typer(nudge.app,        name="nudge",       rich_help_panel="Productivity")
app.add_typer(mcp_cmd.app,      name="mcp",         rich_help_panel="Agent / Dev")
app.add_typer(schema.app,       name="schema",      rich_help_panel="Agent / Dev", hidden=True)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-v",
        help="Print the CLI version.",
        is_eager=True,
    ),
    json_flag: bool = typer.Option(
        False, "--json",
        help="Output machine-readable JSON to stdout (for AI agents / scripts).",
        is_eager=True,
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y",
        help="Skip all interactive confirmations.",
        is_eager=True,
    ),
    debug: bool = typer.Option(
        False, "--debug",
        help="Log full HTTP request/response to ~/.config/kolay/debug.log",
        is_eager=True,
        hidden=True,
    ),
) -> None:
    """Kolay IK CLI / MCP (ALPHA RELEASE)
    Unofficial tool. Use with caution.
    """
    from .ui.output import set_json_mode, set_yes_mode, is_json_mode, json_output

    if json_flag:
        set_json_mode(True)
    if yes:
        set_yes_mode(True)

    if version:
        if is_json_mode():
            json_output({"version": __version__})
        else:
            console.print(f"Kolay CLI version [bold {_PRIMARY}]{__version__}[/bold {_PRIMARY}]")
        raise typer.Exit()

    if debug:
        _enable_debug_logging()

    if ctx.invoked_subcommand is None:
        if not is_json_mode():
            # No sub-command show logo then the help panel
            console.print(_LOGO, no_wrap=True, crop=False)

            # First-run detection: nudge the user towards `kolay setup`
            from .config import CONFIG_FILE_JSON, CONFIG_FILE_YAML
            from .security import is_first_run
            if is_first_run() and not CONFIG_FILE_YAML.exists() and not CONFIG_FILE_JSON.exists():
                console.print(
                    f" [bold {_PRIMARY}]Looks like your first time here![/bold {_PRIMARY}]\n"
                    f" Run [bold]kolay setup[/bold] to authenticate and get started in under a minute.\n"
                )
            else:
                console.print(ctx.get_help())

                # Behavioral Nudge: Contextual bare-command hint
                try:
                    from .services import nudge as nudge_svc
                    if not nudge_svc.should_throttle_bare_command():
                        pending = nudge_svc.analyze_pending_work()
                        if pending:
                            console.print(
                                f"\n  [{WARNING}]Coach's Tip:[/{WARNING}] "
                                f"You have [bold]{len(pending)}[/bold] pending items to review. "
                                f"Run [bold]kolay nudge status[/bold] to see your top priority."
                            )
                        nudge_svc.record_bare_nudge_shown()
                except Exception:
                    pass


def _enable_debug_logging() -> None:
    """Configure debug logging."""
    import logging
    from pathlib import Path

    log_dir = Path.home() / ".config" / "kolay"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "debug.log"

    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    logger = logging.getLogger("kolay.api")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.propagate = False

    # Also flip the KolayClient debug flag
    from .api.client import KolayClient
    KolayClient.debug = True

    console.print(f"[grey62]  Debug logging enabled {log_file}[/grey62]")


if __name__ == "__main__":
    app()
