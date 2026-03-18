"""ASCII detective badge renderer for streak milestones."""
from __future__ import annotations
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


BADGE_TEMPLATE = """
     +==========================+
     |  VERI DEDEKTIFI          |
     |  +--------------------+  |
     |  |  {days:^4} GUN        |  |
    ║  │     SERİSİ!        │  ║
    ║  └────────────────────┘  ║
    ║  {rank:<24}║
    ╚══════════════════════════╝
"""


def render_streak_badge(console: Console, streak: int, rank: str) -> None:
    """Render an ASCII detective badge for streak milestones."""
    badge = BADGE_TEMPLATE.format(days=streak, rank=rank)
    console.print(
        Panel(
            Text(badge, style="bold yellow", justify="center"),
            border_style="yellow",
            expand=False,
            title="[bold yellow]Badge Earned![/bold yellow]",
        )
    )


def render_rank_card(console: Console, rank: str, points: int, streak: int, lang: str = "en") -> None:
    """Render the detective rank card for the `kolay quiz rank` command."""
    from .state import RANKS
    current_tier = 0
    next_tier_points = None
    for i, (threshold, tr_name, en_name) in enumerate(RANKS):
        if tr_name == rank:
            current_tier = i
            if i + 1 < len(RANKS):
                next_tier_points = RANKS[i + 1][0]
            break

    if lang == "tr":
        rank_display = rank
        points_label = "Toplam Puan"
        streak_label = "Seri"
        next_label = "Sonraki Rütbe"
        max_label = "En yüksek rütbeye ulaştınız!"
        days_label = "gün"
        title_label = "Detective ID"
    else:
        # Show English rank name
        rank_display = next((en for _, tr, en in RANKS if tr == rank), rank)
        points_label = "Total Points"
        streak_label = "Streak"
        next_label = "Next Rank"
        max_label = "Maximum rank achieved!"
        days_label = "days"
        title_label = "Detective ID"

    lines = [
        "",
        f"  [bold yellow]{rank_display}[/bold yellow]",
        "",
        f"  [grey62]{points_label}:[/grey62]  [bold white]{points}[/bold white]",
        f"  [grey62]{streak_label}:     [/grey62]  [bold white]{streak} {days_label}[/bold white]",
    ]
    if next_tier_points is not None:
        remaining = next_tier_points - points
        lines.append(f"  [grey62]{next_label}:[/grey62] [yellow]{remaining} pts more[/yellow]")
    else:
        lines.append(f"  [yellow]{max_label}[/yellow]")

    lines.append("")
    box = "\n".join(lines)
    console.print(
        Panel(
            box,
            border_style="yellow",
            title=f"[bold yellow]{title_label}[/bold yellow]",
            expand=False,
        )
    )
