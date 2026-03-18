from __future__ import annotations

import typer
from rich.console import Console

from ..ui.constants import PRIMARY
from ..services.quiz import get_factory, QuizState, Renderer, KolayAPIProvider, MockProvider, QuizEngine

app = typer.Typer(help="Play Kolay Quiz.")
console = Console(highlight=False)


@app.callback(invoke_without_command=True)
def _main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        from ..ui import no_command_help
        no_command_help(ctx)


@app.command(name="play")
def play(
    mode: str = typer.Option("photo_match", "--mode", "-m", help="Game mode to play."),
    count: int = typer.Option(5, "--count", "-c", min=1, max=50, help="Number of questions."),
    mock: bool = typer.Option(False, "--mock", help="Use mock data (for testing/demo without an API token)."),
) -> None:
    """Start a new quiz session."""
    factory = get_factory()
    modes = factory.available_modes()

    if mode not in modes:
        console.print(f"[red]Unknown mode '{mode}'. Available modes: {', '.join(modes)}[/red]")
        raise typer.Exit(1)

    data_provider = MockProvider() if mock else KolayAPIProvider()

    # Early auth check
    if not mock:
        from ..api.client import KolayClient
        from ..api.errors import NotAuthenticatedError
        try:
            # this will raise if not initialized/authenticated
            KolayClient()
        except NotAuthenticatedError:
            console.print("[red]Not authenticated. Use --mock or run `kolay auth login` first.[/red]")
            raise typer.Exit(4)

    provider = factory.get_provider(mode, data_provider)
    state = QuizState.load()
    renderer = Renderer(console=console)

    engine = QuizEngine(provider, renderer, state)

    result = engine.play(num_questions=count)

    if result.total == 0:
        raise typer.Exit(0)

    console.print(f"\n[bold {PRIMARY}]Quiz Complete![/bold {PRIMARY}]\n")
    console.print(f"You scored [bold green]{result.score}[/bold green] out of {result.total}.")

    if result.streak_updated:
        console.print(f"🔥 Daily streak increased to [bold]{state.current_streak}[/bold] days!")
    else:
        console.print(f"Current streak: [bold]{state.current_streak}[/bold] days.")
    console.print()

@app.command(name="stats")
def stats() -> None:
    """View your quiz statistics and high score."""
    state = QuizState.load()
    console.print(f"\n[bold {PRIMARY}]Your Kolay Quiz Stats[/bold {PRIMARY}]\n")
    console.print(f"  High Score:      [bold green]{state.high_score}[/bold green]")
    console.print(f"  Current Streak:  [bold yellow]{state.current_streak} days[/bold yellow]")
    if state.last_played:
        console.print(f"  Last Played:     [grey62]{state.last_played}[/grey62]")
    console.print(f"  Questions Seen:  [bold]{len(state.seen_question_ids)}[/bold]\n")


@app.command(name="streak")
def streak() -> None:
    """Check your active daily streak."""
    state = QuizState.load()
    console.print(f"\n🔥 Active Streak: [bold {PRIMARY}]{state.current_streak}[/bold {PRIMARY}] days\n")
