"""Behavioral Nudge Engine CLI commands."""
from __future__ import annotations
import typer

from ..services import nudge as svc
from ..ui import (
    console, api_call, print_success,
    is_json_mode, json_output
)
from ..ui.nudge_formatters import (
    print_nudge_card, print_celebration, sprint_prompt,
    print_streak
)

app = typer.Typer(help="Behavioral psychology-driven productivity coaching.")

@app.command(name="status")
def nudge_status() -> None:
    """Show current pending work summary + single actionable nudge."""
    with api_call("Analyzing your pending tasks..."):
        pending = svc.analyze_pending_work()
        prefs = svc.load_preferences()

    if is_json_mode():
        json_output({"pending_count": len(pending), "preferences": prefs, "items": pending})
        return

    if not pending:
        streak = svc.update_streak()
        print_celebration(prefs["style"])
        if prefs["style"] == "gamification":
            print_streak(streak)
        return
        
    print_nudge_card(pending, prefs["style"])

@app.command(name="configure")
def nudge_configure() -> None:
    """Interactive preference setup (cadence, style, sprint duration)."""
    if is_json_mode():
        json_output({"error": "configure is interactive only"})
        raise typer.Exit(1)
        
    console.print("\n[bold]Behavioral Nudge Engine Configuration[/bold]\n")
    
    style = typer.prompt("What is your preferred interaction style? (gentle, gamification, direct)", default="gentle")
    if style not in ["gentle", "gamification", "direct"]:
        style = "gentle"
        
    cadence = typer.prompt("How often should we nudge you defensively? (daily, weekly, never)", default="daily")
    if cadence not in ["daily", "weekly", "never"]:
        cadence = "daily"
        
    sprint_duration = typer.prompt("How many minutes should a productivity sprint last?", default="5")
    try:
        sprint_duration = int(sprint_duration)
    except ValueError:
        sprint_duration = 5
        
    prefs = svc.load_preferences()
    prefs.update({
        "style": style,
        "cadence": cadence,
        "sprint_duration": sprint_duration
    })
    svc.save_preferences(prefs)
    
    print_success("Behavioral coaching preferences saved successfully.")


@app.command(name="sprint")
def nudge_sprint() -> None:
    """Start a time-boxed micro-sprint for pending tasks."""
    if is_json_mode():
        json_output({"error": "sprint is interactive only"})
        raise typer.Exit(1)
        
    with api_call("Loading sprint data..."):
        pending = svc.analyze_pending_work()
        prefs = svc.load_preferences()
        
    if not pending:
        streak = svc.update_streak()
        print_celebration(prefs["style"])
        if prefs["style"] == "gamification":
            print_streak(streak)
        return
        
    console.print(f"\n[bold]Starting your {prefs['sprint_duration']}-minute micro-sprint...[/bold]")
    sprint_prompt(pending, prefs["style"])
