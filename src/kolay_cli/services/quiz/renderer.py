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
                try:
                    import requests
                    import base64
                    import sys
                    import os
                    self.console.print(f"🖼️  [link={media.content}]Photo details (Cmd+Click to open)[/link]")
                    
                    # Fetch and convert to iTerm2 inline protocol (supported by VSCode, iTerm, WezTerm, etc.)
                    resp = requests.get(media.content, timeout=5)
                    if resp.status_code == 200:
                        term_prog = os.environ.get("TERM_PROGRAM", "")
                        # Try high-res native rendering for supported multiplexers
                        if term_prog in ("iTerm.app", "vscode", "WezTerm", "Ghostty") or "kitty" in os.environ.get("TERM", ""):
                            img_b64 = base64.b64encode(resp.content).decode("ascii")
                            # height=12 forces it to take up about 12 lines of terminal vertical space
                            sys.stdout.write(f"\033]1337;File=inline=1;height=12;preserveAspectRatio=1:{img_b64}\a\n")
                            sys.stdout.flush()
                        else:
                            # Graceful fallback: Braille-based ASCII art for standard terminals (like Apple Terminal)
                            from io import BytesIO
                            try:
                                from PIL import Image
                                from rich_pixels import Pixels
                                
                                with Image.open(BytesIO(resp.content)) as image:
                                    # Ensure image is small enough for 1x zoom rendering
                                    image.thumbnail((60, 60))
                                    pixels = Pixels.from_image(image)
                                    self.console.print(pixels)
                            except ImportError:
                                self.console.print("[grey62](Native rendering unavailable. Install `Pillow` & `rich-pixels` for ASCII mode)[/grey62]")
                    else:
                        raise ValueError(f"HTTP {resp.status_code}")
                except Exception as e:
                    self.console.print(
                        Panel(
                            f"\n[grey62](Could not load terminal image: {e})[/grey62]",
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
