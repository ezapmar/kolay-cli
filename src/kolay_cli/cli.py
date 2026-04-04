"""Kolay CLI entry point."""
from __future__ import annotations
import typer
from rich.console import Console

from . import __version__


from .commands import (
    auth, person, leave, timelog, training, transaction, calendar,
    unit, approval, payroll, expense, nudge, schema, doctor, setup,
    quiz, status, analytics
)
from .commands import config as config_cmd
from .commands import mcp as mcp_cmd
from .commands import rag as rag_cmd

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
app.add_typer(analytics.app,    name="analytics",   rich_help_panel="Productivity")
app.add_typer(quiz.app,         name="quiz",        rich_help_panel="Fun")
app.add_typer(mcp_cmd.app,      name="mcp",         rich_help_panel="Agent / Dev")
app.add_typer(schema.app,       name="schema",      rich_help_panel="Agent / Dev")
app.add_typer(rag_cmd.app,      name="rag",         rich_help_panel="Agent / Dev")

@app.command(rich_help_panel="Getting Started")
def status() -> None:
    """Print a compact dashboard of your current HR status."""
    from .commands.status import run_status
    run_status()
@app.command(rich_help_panel="Authentication")
def whoami() -> None:
    """Shortcut for 'kolay auth me'. Shows your currently authenticated profile."""
    auth.me()



@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-v",
        help="Print the CLI version.",
        is_eager=True,
    ),
    changelog: bool = typer.Option(
        False, "--changelog",
        help="View the latest release changes.",
        is_eager=True,
    ),
    json_flag: bool = typer.Option(
        False, "--json",
        help="Output machine-readable JSON to stdout (for AI agents / scripts).",
        is_eager=True,
    ),
    format_opt: str = typer.Option(
        "", "--format", "-f",
        help="Output format: table, json, csv, tsv.",
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
    from .ui.output import set_json_mode, set_yes_mode, set_format_mode, is_json_mode, json_output

    if json_flag:
        set_json_mode(True)
    if format_opt:
        set_format_mode(format_opt)
    if yes:
        set_yes_mode(True)

    if not is_json_mode() and ctx.invoked_subcommand not in {None, "setup", "auth", "mcp"}:
        from .security import resolve_token, _is_jwt, _decode_jwt_claims
        import time
        token = resolve_token()
        if token and _is_jwt(token):
            claims = _decode_jwt_claims(token)
            if claims and claims.get("exp"):
                rem = claims["exp"] - int(time.time())
                if 0 < rem < 3600:
                    console.print(f" [bold #FFD93D]Warning:[/bold #FFD93D] Your API token expires in {rem // 60} mins. Run [bold]kolay auth login[/bold] soon.\n")

    if version:
        if is_json_mode():
            json_output({"version": __version__})
        else:
            console.print(f"Kolay CLI version [bold {_PRIMARY}]{__version__}[/bold {_PRIMARY}] (ALPHA RELEASE)")
        raise typer.Exit()

    if changelog:
        with console.status("Fetching latest changelog...", spinner="dots"):
            import requests # default dep
            try:
                resp = requests.get(
                    "https://api.github.com/repos/ezapmar/kolay-cli/releases",
                    timeout=5,
                )
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    console.print("[yellow]No releases found.[/yellow]")
                    raise typer.Exit()
                
                latest = data[0]
                from rich.markdown import Markdown
                console.print(f"\n[bold {_PRIMARY}]Kolay CLI — What's New ({latest.get('tag_name')})[/bold {_PRIMARY}]\n")
                console.print(Markdown(latest.get("body", "No release notes available.")))
            except Exception as e:
                console.print(f"[red]Could not fetch changelog: {e}[/red]")
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
                except ImportError as exc:
                    import logging
                    logging.getLogger(__name__).debug("Failed to load nudge module: %s", exc)


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


def run() -> None:
    """CLI entry point wrapper for hooking global usage analytics."""
    import sys
    import time
    from . import analytics

    start = time.monotonic()
    success = True
    try:
        app()
    except SystemExit as e:
        success = (e.code == 0 or e.code is None)
        raise
    except Exception:
        success = False
        raise
    finally:
        try:
            if analytics.is_enabled():
                cmd = " ".join([arg for arg in sys.argv[1:3] if not arg.startswith("-")])
                cmd = cmd.strip() or "main"
                analytics.record(cmd, duration_ms=(time.monotonic() - start) * 1000, success=success)
        except Exception:
            pass

if __name__ == "__main__":
    run()
