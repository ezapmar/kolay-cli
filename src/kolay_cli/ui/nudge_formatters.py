"""UI formatters specifically for behavioral nudges."""
from __future__ import annotations
import random
from typing import Any
from rich.panel import Panel

from .constants import PRIMARY, ACCENT, SUCCESS, WARNING, ERROR
from . import console

def print_nudge_card(pending: list[dict[str, Any]], style: str) -> None:
    """Render a single actionable nudge card avoiding task dumps."""
    count = len(pending)
    top_item = pending[0]
    
    title = "[bold]AI Coach Suggestion[/bold]"
    
    if count > 10:
        # Overwhelmed state
        message = (
            f"You have {count} items pending. That's a lot of cognitive load! "
            f"Let's ignore {count-1} of them right now and just focus on one quick win:\n\n"
            f"[bold {ACCENT}]> {top_item['title']}[/bold {ACCENT}] — {top_item['detail']}\n\n"
            f"Run [bold]kolay nudge sprint[/bold] to knock a few out in 5 minutes."
        )
    else:
        # Moderate state
        if style == "gamification":
            message = (
                f"You're almost caught up! Only {count} items left to clear your queue.\n\n"
                f"Next up for EXP:\n"
                f"[bold {ACCENT}]> {top_item['title']}[/bold {ACCENT}] — {top_item['detail']}\n\n"
                f"Approve this item using [bold]kolay {top_item['type']} view {top_item['id']}[/bold]"
            )
        elif style == "direct":
            message = (
                f"{count} pending. Top priority:\n\n"
                f"[bold {ACCENT}]> {top_item['title']}[/bold {ACCENT}] — {top_item['detail']}\n\n"
                f"Action: [bold]kolay {top_item['type']} view {top_item['id']}[/bold]"
            )
        else:
            # gentle
            message = (
                f"You have {count} items pending when you have a moment.\n"
                f"Here is the most recent one to look at:\n\n"
                f"[bold {ACCENT}]> {top_item['title']}[/bold {ACCENT}] — {top_item['detail']}\n\n"
                f"You can handle it with: [bold]kolay {top_item['type']} view {top_item['id']}[/bold]"
            )

    panel = Panel(
        message,
        title=title,
        title_align="left",
        border_style=ACCENT,
        padding=(1, 2)
    )
    console.print(panel)

def print_celebration(style: str) -> None:
    """Positive reinforcement copy."""
    messages = [
        "Incredible! Zero pending items. Your workspace is perfectly clean.",
        "Nice work! Queue is empty. That's how we build momentum.",
        "All clear! You've successfully conquered the dashboard."
    ]
    if style == "gamification":
        messages = [
            "Level up! Zero pending items.",
            "Queue completely cleared! +100 Productivity EXP."
        ]
    elif style == "direct":
        messages = [
            "0 items pending. Queue clear."
        ]
        
    msg = random.choice(messages)
    console.print(f"\n[bold {SUCCESS}]{msg}[/bold {SUCCESS}]")

def print_streak(count: int) -> None:
    """Display gamification streak."""
    if count >= 3:
        console.print(f"[{WARNING}]You are on a {count}-day streak of keeping your queue clean! Keep it alive![/{WARNING}]\n")
    else:
        console.print(f"[{SUCCESS}]Streak started! Day {count}.[/{SUCCESS}]\n")

def sprint_prompt(pending: list[dict[str, Any]], style: str) -> None:
    """Show items one by one for a micro-sprint."""
    for i, item in enumerate(pending[:5]): # Only sprint up to 5 at a time
        console.print(f"\n[bold]Task {i+1}/{min(5, len(pending))}[/bold]: {item['title']}")
        console.print(f"[{ACCENT}]Detail:[/{ACCENT}] {item['detail']}")
        console.print(f"[{PRIMARY}]Action:[/{PRIMARY}] run `kolay {item['type']} view {item['id']}` to approve.")
    
    console.print(f"\n[bold {SUCCESS}]Sprint complete! You are doing great.[/bold {SUCCESS}]")
    if len(pending) > 5:
        console.print(f"There are still {len(pending)-5} items left. Run [bold]kolay nudge sprint[/bold] again when you're ready.")

def print_cross_service_nudge(pending: list[dict[str, Any]], source: str) -> None:
    """Print cross-service nudge hint."""
    other_pending = [p for p in pending if p["type"] != source]
    if not other_pending:
        return
    
    count = len(other_pending)
    console.print(
        f"\n[{WARNING}]Coach's Nudge:[/{WARNING}] "
        f"You have {count} pending items in other areas (like a {other_pending[0]['title']}). "
        f"Clear them in 5 mins with [bold]kolay nudge sprint[/bold]!"
    )
