"""View or manage your local CLI analytics."""
from __future__ import annotations

import typer
from rich.panel import Panel
from rich.table import Table

from ..ui import console, PRIMARY, WARNING, is_json_mode, json_output
from .. import analytics as engine

app = typer.Typer(help="View or manage local usage analytics.")


@app.callback(invoke_without_command=True)
def view(
    ctx: typer.Context,
    reset: bool = typer.Option(False, "--reset", help="Wipe all analytics data."),
    enable: bool = typer.Option(False, "--enable", help="Opt-in to analytics data collection."),
    disable: bool = typer.Option(False, "--disable", help="Opt-out of analytics data collection.")
) -> None:
    """Show your personal CLI usage dashboard. Data never leaves your machine."""
    
    if enable:
        from ..config import set_config_value
        set_config_value("analytics_enabled", True)
        if not is_json_mode():
            console.print(f" [bold {PRIMARY}]Analytics enabled![/bold {PRIMARY}] Data is stored locally.")
        return

    if disable:
        from ..config import set_config_value
        set_config_value("analytics_enabled", False)
        # We can also wipe on opt-out
        engine.reset()
        if not is_json_mode():
            console.print(f" [bold {WARNING}]Analytics disabled & wiped![/bold {WARNING}]")
        return

    if reset:
        engine.reset()
        if not is_json_mode():
            console.print(" [grey62]All analytics data wiped.[/grey62]")
        return
        
    # Standard view
    is_on = engine.is_enabled()
    if not is_on:
        if is_json_mode():
            json_output({"enabled": False, "message": "Analytics disabled."})
        else:
            console.print(
                f"\n [grey62]Analytics is currently disabled.[/grey62]\n"
                f" Run [bold]kolay analytics --enable[/bold] to start logging your usage locally.\n"
            )
        return

    data = engine.summarize()
    if is_json_mode():
        json_output(data)
        return

    # Render dashboard
    console.print(f"\n[bold {PRIMARY}]Your CLI Stats[/bold {PRIMARY}]  [grey62](Local-only)[/grey62]\n")
    
    if data.get("total_commands") == 0:
        console.print(" [grey62]No data yet. Run some commands![/grey62]\n")
        return

    # Basic stats
    console.print(f" [bold]Total commands:[/bold] {data['total_commands']} (across {data['active_days']} days)")
    console.print(f" [bold]Average time:  [/bold] {data['avg_duration_ms']}ms per command")
    console.print(f" [bold]Error rate:    [/bold] [red]{data['error_rate_pct']}%[/red] ({data['error_count']} failed)")
    console.print(f" [bold]Busiest day:   [/bold] {data['busiest_weekday']}")
    console.print(f" [bold]Current streak:[/bold] [orange1]{data['current_streak']} days[/orange1] [STREAK]\n")

    # Top commands table
    tbl = Table(box=None, show_edge=False, header_style=f"bold {PRIMARY}")
    tbl.add_column("Command", style="bold white")
    tbl.add_column("Count", style="grey62", justify="right")
    
    for cmd, count in data.get("top_commands", []):
        tbl.add_row(cmd, str(count))
        
    console.print(Panel(tbl, title="Top Commands", border_style="grey62", expand=False))
    console.print()
