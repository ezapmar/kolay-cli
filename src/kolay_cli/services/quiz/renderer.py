from __future__ import annotations
import time
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ...ui.constants import PRIMARY
from .base import BaseQuestion, MediaType


class Renderer:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console(highlight=False)

    def clear(self) -> None:
        self.console.clear()

    def show_title(self, title: str) -> None:
        self.console.print(f"\n[bold {PRIMARY}]{title}[/bold {PRIMARY}]\n", justify="center")

    def show_question(self, q: BaseQuestion) -> None:
        media = q.media()
        if media:
            if media.type == MediaType.PHOTO_URL:
                # ASCII fallback implementation. Real image proto could be added later.
                self.console.print(
                    Panel(
                        f"🖼️  [link={media.content}]Photo link[/link]\n[grey62]Terminal image protocol support coming later.[/grey62]",
                        border_style=PRIMARY,
                        width=60,
                    )
                )
            else:
                self.console.print(Panel(media.content, border_style=PRIMARY, width=60))

        self.console.print(f"\n[bold]{q.prompt_text()}[/bold]\n")

        for i, choice in enumerate(q.choices(), 1):
            self.console.print(f"  [bold {PRIMARY}]{i}.[/bold {PRIMARY}] {choice}")
        self.console.print()

    def get_answer(self, max_choices: int) -> int:
        while True:
            ans = Prompt.ask(f"[{PRIMARY}]Your answer (1-{max_choices})[/{PRIMARY}]")
            if ans.isdigit() and 1 <= int(ans) <= max_choices:
                return int(ans)
            self.console.print("[red]Invalid choice, please enter a valid number.[/red]")

    def show_result(self, is_correct: bool, correct: str, explanation: str) -> None:
        if is_correct:
            self.console.print(f"\n[bold green]✓ Correct![/bold green] {explanation}")
        else:
            self.console.print(
                f"\n[bold red]✗ Incorrect.[/bold red] The right answer was [bold]{correct}[/bold].\n[grey62]{explanation}[/grey62]"
            )
        time.sleep(2)
