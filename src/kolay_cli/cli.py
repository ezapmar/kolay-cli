"""
Kolay CLI — entry point.

Global flags:
  --version / -v   Print the CLI version and exit.
  --json           Output machine-readable JSON to stdout (for AI agents / scripts).
  --yes / -y       Skip all interactive confirmations.
  --debug          Enable verbose HTTP logging to ~/.config/kolay/debug.log
"""
from __future__ import annotations
import typer
from rich.console import Console

from . import __version__

# Lazy command group imports — speeds up startup for all non-invoked groups
from .commands import (
    auth, person, leave, transaction, calendar,
    timelog, training, unit, expense, approval, schema
)
from .commands import config as config_cmd  # avoid shadowing built-in
from .commands import mcp as mcp_cmd

_LOGO = """
[bold #376BFB]       ##################[/bold #376BFB]
[bold #376BFB]      ###            ###[/bold #376BFB]
[bold #376BFB]    ####           ####        %%%                       %%%[/bold #376BFB]
[bold #376BFB]   ####           ####         %%%                       %%%[/bold #376BFB]
[bold #376BFB]  ####           ####          %%%                       %%%[/bold #376BFB]
[bold #376BFB] ####           ####           %%%   %%%%   %%%%%%%%%    %%%    %%%%%%%%%%%  %%%     %%%% [/bold #376BFB]
[bold #376BFB]####           ###             %%%  %%%%  %%%%%   %%%%   %%%  %%%%%   %%%%%  %%%%    %%% [/bold #376BFB]
[bold #376BFB]####          #####            %%%%%%%    %%%       %%%  %%%  %%%       %%%   %%%%  %%%% [/bold #376BFB]
[bold #376BFB] ####       ########           %%%%%%%    %%%       %%%  %%%  %%%       %%%    %%%%%%%% [/bold #376BFB]
[bold #376BFB]  ####     ####  ####          %%% %%%%   %%%%     %%%%  %%%  %%%%     %%%%     %%%%%% [/bold #376BFB]
[bold #376BFB]   ####   ####    ####         %%%   %%%%  %%%%%%%%%%%   %%%   %%%%%%%%%%%%      %%%% [/bold #376BFB]
[bold #376BFB]     ### ####      ####        %%%     %%%    %%%%%      %%%      %%%%  %%%      %%%% [/bold #376BFB]
[bold #376BFB]      #####          ###                                                       %%%%% [/bold #376BFB]
[bold #376BFB]       ##################                                                     %%%%% [/bold #376BFB]
"""

app = typer.Typer(
    no_args_is_help=False,   # we handle the no-args case ourselves to show the logo
    rich_markup_mode="rich",
)
console = Console(highlight=False)

# ── Command groups ─────────────────────────────────────────────────────────────
app.add_typer(auth.app,         name="auth",        rich_help_panel="Authentication")
app.add_typer(config_cmd.app,   name="config",      rich_help_panel="Authentication")
app.add_typer(person.app,       name="person",      rich_help_panel="People")
app.add_typer(leave.app,        name="leave",       rich_help_panel="People")
app.add_typer(timelog.app,      name="timelog",      rich_help_panel="People")
app.add_typer(training.app,     name="training",    rich_help_panel="People")
app.add_typer(transaction.app,  name="transaction", rich_help_panel="Finance")
app.add_typer(expense.app,      name="expense",     rich_help_panel="Finance")
app.add_typer(approval.app,     name="approval",    rich_help_panel="Workflows")
app.add_typer(calendar.app,     name="calendar",    rich_help_panel="Workflows")
app.add_typer(unit.app,         name="unit",        rich_help_panel="Organisation")
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
    """Kolay IK command-line interface.

    Run any sub-command with --help for detailed usage.

    Use --json for structured output consumable by AI agents and scripts.
    Use --yes to skip confirmation prompts in non-interactive environments.
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
            console.print(f"Kolay CLI  [bold #376BFB]{__version__}[/bold #376BFB]")
        raise typer.Exit()

    if debug:
        _enable_debug_logging()

    if ctx.invoked_subcommand is None:
        if not is_json_mode():
            # No sub-command → show logo then the help panel
            console.print(_LOGO, no_wrap=True, crop=False)
            console.print(ctx.get_help())


def _enable_debug_logging() -> None:
    """Configure file-based debug logging for the kolay.api logger."""
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

    console.print(f"[grey62]  Debug logging enabled → {log_file}[/grey62]")


if __name__ == "__main__":
    app()
