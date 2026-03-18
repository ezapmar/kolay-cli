from __future__ import annotations

import typer
from rich.console import Console

from ..services.quiz import get_factory, QuizState, Renderer, KolayAPIProvider, MockProvider, QuizEngine

app = typer.Typer(help="🔍 Veri Dedektifi — Data Detective. Know your company's secrets.")
console = Console(highlight=False)


@app.callback(invoke_without_command=True)
def _main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        from ..ui import no_command_help
        no_command_help(ctx)


@app.command(name="play")
def play(
    mode: str = typer.Option(
        "photo_match",
        "--mode", "-m",
        help="Game mode. Choices: photo_match, education_champion, unique_title, december_exodus"
    ),
    count: int = typer.Option(5, "--count", "-c", min=1, max=50, help="Number of cases."),
    mock: bool = typer.Option(False, "--mock", help="Use mock data (for testing/demo without an API token)."),
    hints: bool = typer.Option(True, "--hints/--no-hints", help="Enable or disable the hint system."),
) -> None:
    """Start a new Veri Dedektifi session. Solve the cases. Earn your badge."""
    factory = get_factory()
    modes = factory.available_modes()

    if mode not in modes:
        console.print(f"[red]Bilinmeyen mod '{mode}'.[/red]")
        console.print(f"[grey62]Mevcut modlar: {', '.join(modes)}[/grey62]")
        raise typer.Exit(1)

    data_provider = MockProvider() if mock else KolayAPIProvider()

    # Early auth check
    if not mock:
        from ..api.client import KolayClient
        try:
            KolayClient()
        except Exception:
            console.print("[red]Kimlik doğrulaması başarısız. --mock kullanın veya önce `kolay auth login` çalıştırın.[/red]")
            raise typer.Exit(4)

    provider = factory.get_provider(mode, data_provider)
    state = QuizState.load()
    renderer = Renderer(console=console)

    engine = QuizEngine(provider, renderer, state, hints_enabled=hints)
    result = engine.play(num_questions=count)

    if result.total == 0:
        raise typer.Exit(0)

    console.print(f"\n[bold yellow]🔍 Tüm Davalar Çözüldü![/bold yellow]\n")
    console.print(f"  Doğru: [bold green]{result.score}[/bold green] / {result.total}")
    console.print(f"  Bu turda kazanılan puan: [bold yellow]+{result.points_earned}[/bold yellow]")
    console.print(f"  Toplam puan: [bold]{state.total_case_points}[/bold]")
    console.print(f"  Rütbe: [bold yellow]{state.rank}[/bold yellow]")

    if result.streak_updated:
        console.print(f"\n🔥 Günlük seri: [bold]{state.current_streak}[/bold] gün!")
    else:
        console.print(f"\n  Günlük seri: [bold]{state.current_streak}[/bold] gün")
    console.print()


@app.command(name="stats")
def stats() -> None:
    """View your detective case stats and high score."""
    state = QuizState.load()
    console.print(f"\n[bold yellow]🕵️  Dedektif İstatistikleri[/bold yellow]\n")
    console.print(f"  Rekor:           [bold green]{state.high_score}[/bold green]")
    console.print(f"  Günlük Seri:     [bold yellow]{state.current_streak} gün[/bold yellow]")
    console.print(f"  Toplam Puan:     [bold]{state.total_case_points}[/bold]")
    console.print(f"  Rütbe:           [bold yellow]{state.rank}[/bold yellow]")
    console.print(f"  Kullanılan İpucu:[bold]{state.hints_used}[/bold]")
    if state.last_played:
        console.print(f"  Son Oynama:      [grey62]{state.last_played}[/grey62]")
    console.print(f"  Çözülen Dava:    [bold]{len(state.seen_question_ids)}[/bold]\n")


@app.command(name="streak")
def streak() -> None:
    """Check your active daily detective streak."""
    state = QuizState.load()
    console.print(f"\n🔥 Aktif Seri: [bold yellow]{state.current_streak}[/bold yellow] gün\n")


@app.command(name="rank")
def rank() -> None:
    """Display your detective rank card."""
    from ..services.quiz.badges import render_rank_card
    state = QuizState.load()
    render_rank_card(console, state.rank, state.total_case_points, state.current_streak)
