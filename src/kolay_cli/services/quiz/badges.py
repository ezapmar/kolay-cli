"""ASCII detective badge renderer for streak milestones."""
from __future__ import annotations
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


BADGE_TEMPLATE = """
    ╔══════════════════════════╗
    ║  🔍  VERİ DEDEKTİFİ    ║
    ║  ┌────────────────────┐  ║
    ║  │  🏆  {days:^4} GÜN  │  ║
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
            title="[bold yellow]🎖️  Rozet Kazandı![/bold yellow]",
        )
    )


def render_rank_card(console: Console, rank: str, points: int, streak: int) -> None:
    """Render the detective rank card for the `kolay quiz rank` command."""
    # Find rank tier for progress info
    from .state import RANKS
    current_tier = 0
    next_tier_points = None
    for i, (threshold, tr_name, _) in enumerate(RANKS):
        if tr_name == rank:
            current_tier = i
            if i + 1 < len(RANKS):
                next_tier_points = RANKS[i + 1][0]
            break

    lines = [
        "",
        f"  [bold yellow]🔍  {rank}[/bold yellow]",
        "",
        f"  [grey62]Toplam Puan:[/grey62]  [bold white]{points}[/bold white]",
        f"  [grey62]Seri:        [/grey62]  [bold white]{streak} gün[/bold white]",
    ]
    if next_tier_points is not None:
        remaining = next_tier_points - points
        lines.append(f"  [grey62]Sonraki Rütbe:[/grey62] [yellow]{remaining} puan daha[/yellow]")
    else:
        lines.append("  [yellow]En yüksek rütbeye ulaştınız![/yellow]")

    lines.append("")
    box = "\n".join(lines)
    console.print(
        Panel(
            box,
            border_style="yellow",
            title="[bold yellow]🕵️  Dedektif Kimliği[/bold yellow]",
            expand=False,
        )
    )
