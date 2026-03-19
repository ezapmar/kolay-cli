from __future__ import annotations
from typing import Optional
import typer
from rich.console import Console

from ..services.quiz import get_factory, QuizState, Renderer, KolayAPIProvider, MockProvider, QuizEngine

app = typer.Typer(help="Data Detective -- uncover secrets hidden in your HR data.")
console = Console(highlight=False)

LANG_HELP = "UI language: 'en' (default) or 'tr' for Turkish."


@app.callback(invoke_without_command=True)
def _main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        from ..ui import no_command_help
        no_command_help(ctx)


@app.command(name="play")
def play(
    mode: Optional[str] = typer.Option(
        None,
        "--mode", "-m",
        help="Game mode: photo_match, education_champion, unique_title, december_exodus"
    ),
    count: int = typer.Option(5, "--count", "-c", min=1, max=50, help="Number of cases per session."),
    mock: bool = typer.Option(False, "--mock", help="Use mock data (no API token needed)."),
    hints: bool = typer.Option(True, "--hints/--no-hints", help="Enable / disable the hint system."),
    lang: str = typer.Option("en", "--lang", help=LANG_HELP),
) -> None:
    """Start a new Data Detective session. Solve cases. Earn your rank."""
    factory = get_factory()
    modes = factory.available_modes()

    if mode is None:
        from rich.prompt import IntPrompt
        from ..ui.constants import PRIMARY
        console.print(f"\n[{PRIMARY}]Available Cases:[/]\n")
        
        mode_labels = {
            "photo_match": "Face ID (Who is this?)", 
            "education_champion": "Academic Degrees",
            "unique_title": "Lonely Roles (Org Chart)",
            "december_exodus": "Leave Time Machine",
        }

        for i, m in enumerate(modes, 1):
            lbl = mode_labels.get(m, m)
            console.print(f"  [bold cyan]{i}.[/] {lbl} [grey62]({m})[/]")
        
        console.print()
        choice = IntPrompt.ask("Select a case to solve", choices=[str(i) for i in range(1, len(modes) + 1)], show_choices=False)
        mode = modes[choice - 1]
    elif mode not in modes:
        console.print(f"[red]Unknown mode '{mode}'.[/red]")
        console.print(f"[grey62]Available modes: {', '.join(modes)}[/grey62]")
        raise typer.Exit(1)

    if lang not in ("en", "tr"):
        console.print(f"[red]Unknown language '{lang}'. Use 'en' or 'tr'.[/red]")
        raise typer.Exit(2)

    data_provider = MockProvider() if mock else KolayAPIProvider()

    if not mock:
        from ..api.client import KolayClient
        try:
            KolayClient()
        except Exception:
            console.print("[red]Authentication failed. Use --mock or run `kolay auth login` first.[/red]")
            raise typer.Exit(4)

    provider = factory.get_provider(mode, data_provider)
    state = QuizState.load()
    renderer = Renderer(console=console, lang=lang)
    engine = QuizEngine(provider, renderer, state, hints_enabled=hints, lang=lang)

    from ..api.errors import APIError
    try:
        result = engine.play(num_questions=count)
    except APIError as exc:
        status = getattr(exc, "status_code", None)
        if status in (400, 401, 403):
            console.print(
                f"\n[bold red]Authentication error:[/bold red] {exc}\n"
                "Your Kolay API token may be invalid or expired.\n"
                "Run [bold]kolay auth login[/bold] to re-authenticate, then try again."
            )
        else:
            console.print(f"\n[bold red]API error:[/bold red] {exc}")
        raise typer.Exit(4)

    if result.total == 0:
        raise typer.Exit(0)

    # Localised summary
    if lang == "tr":
        console.print(f"\n[bold yellow]Tum Davalar Cozuldu![/bold yellow]\n")
        console.print(f"  Doğru: [bold green]{result.score}[/bold green] / {result.total}")
        console.print(f"  Bu turda kazanılan puan: [bold yellow]+{result.points_earned}[/bold yellow]")
        console.print(f"  Toplam puan: [bold]{state.total_case_points}[/bold]")
        console.print(f"  Rütbe: [bold yellow]{state.rank}[/bold yellow]")
        streak_msg = f"Gunluk seri: [bold]{state.current_streak}[/bold] gun!"
        no_streak_msg = f"  Günlük seri: [bold]{state.current_streak}[/bold] gün"
    else:
        console.print(f"\n[bold yellow]All cases closed![/bold yellow]\n")
        console.print(f"  Correct: [bold green]{result.score}[/bold green] / {result.total}")
        console.print(f"  Points this session: [bold yellow]+{result.points_earned}[/bold yellow]")
        console.print(f"  Total points: [bold]{state.total_case_points}[/bold]")
        console.print(f"  Rank: [bold yellow]{state.rank}[/bold yellow]")
        streak_msg = f"Daily streak: [bold]{state.current_streak}[/bold] days!"
        no_streak_msg = f"  Daily streak: [bold]{state.current_streak}[/bold] days"

    if result.streak_updated:
        console.print(f"\n{streak_msg}")
    else:
        console.print(f"\n{no_streak_msg}")
    console.print()


@app.command(name="stats")
def stats(lang: str = typer.Option("en", "--lang", help=LANG_HELP)) -> None:
    """View your detective case stats and high score."""
    state = QuizState.load()
    if lang == "tr":
        console.print(f"\n[bold yellow]Dedektif Istatistikleri[/bold yellow]\n")
        console.print(f"  Rekor:            [bold green]{state.high_score}[/bold green]")
        console.print(f"  Günlük Seri:      [bold yellow]{state.current_streak} gün[/bold yellow]")
        console.print(f"  Toplam Puan:      [bold]{state.total_case_points}[/bold]")
        console.print(f"  Rütbe:            [bold yellow]{state.rank}[/bold yellow]")
        console.print(f"  Kullanılan İpucu: [bold]{state.hints_used}[/bold]")
        if state.last_played:
            console.print(f"  Son Oynama:       [grey62]{state.last_played}[/grey62]")
        console.print(f"  Çözülen Dava:     [bold]{len(state.seen_question_ids)}[/bold]\n")
    else:
        console.print(f"\n[bold yellow]Detective Stats[/bold yellow]\n")
        console.print(f"  High score:   [bold green]{state.high_score}[/bold green]")
        console.print(f"  Daily streak: [bold yellow]{state.current_streak} days[/bold yellow]")
        console.print(f"  Total points: [bold]{state.total_case_points}[/bold]")
        console.print(f"  Rank:         [bold yellow]{state.rank}[/bold yellow]")
        console.print(f"  Hints used:   [bold]{state.hints_used}[/bold]")
        if state.last_played:
            console.print(f"  Last played:  [grey62]{state.last_played}[/grey62]")
        console.print(f"  Cases solved: [bold]{len(state.seen_question_ids)}[/bold]\n")


@app.command(name="streak")
def streak(lang: str = typer.Option("en", "--lang", help=LANG_HELP)) -> None:
    """Check your active daily detective streak."""
    state = QuizState.load()
    if lang == "tr":
        console.print(f"\nAktif Seri: [bold yellow]{state.current_streak}[/bold yellow] gun\n")
    else:
        console.print(f"\nActive streak: [bold yellow]{state.current_streak}[/bold yellow] days\n")


@app.command(name="rank")
def rank(lang: str = typer.Option("en", "--lang", help=LANG_HELP)) -> None:
    """Display your detective rank card."""
    from ..services.quiz.badges import render_rank_card
    state = QuizState.load()
    render_rank_card(console, state.rank, state.total_case_points, state.current_streak, lang=lang)
