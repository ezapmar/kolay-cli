from __future__ import annotations
import sys
import time
import random
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .base import BaseQuestion, MediaType

# Noir palette
NOIR_BORDER = "grey42"
NOIR_ACCENT = "yellow"
NOIR_DIM = "grey62"

# Locale strings — extend here for more languages
_STRINGS = {
    "en": {
        "hint_ask":     "Want a hint? (-3 pts) (y/n)",
        "hint_label":   "Hint: The answer looks like ->",
        "get_answer":   "Your answer (1-{n})",
        "correct":      "Correct! Case closed.",
        "wrong":        "Wrong.",
        "right_answer": "The correct answer was",
        "invalid":      "Invalid choice -- please enter a valid number.",
        "analyzing":    "Case File",
        "no_data":      "Not enough data to run a session. Try again later.",
    },
    "tr": {
        "hint_ask":     "Ipucu ister misiniz? (-3 puan) (e/h)",
        "hint_label":   "Ipucu: Cevap suna benziyor ->",
        "get_answer":   "Cevabiniz (1-{n})",
        "correct":      "Dogru! Dava kapatildi.",
        "wrong":        "Yanlis.",
        "right_answer": "Dogru cevap:",
        "invalid":      "Gecersiz secim -- lutfen gecerli bir numara girin.",
        "analyzing":    "Dava Dosyasi",
        "no_data":      "Yeterli veri bulunamadi. Lutfen daha sonra tekrar deneyin.",
    },
}


def _mask_answer(answer: str) -> str:
    """Partially mask an answer string. 'Ahmet Yılmaz' → 'A**** Y*****'"""
    parts = answer.split()
    masked = []
    for part in parts:
        if len(part) <= 1:
            masked.append(part)
        else:
            masked.append(part[0] + "*" * (len(part) - 1))
    return " ".join(masked)


class Renderer:
    def __init__(self, console: Console | None = None, lang: str = "en") -> None:
        self.console = console or Console(highlight=False)
        self._s = _STRINGS.get(lang, _STRINGS["en"])

    def clear(self) -> None:
        self.console.clear()

    def show_title(self, title: str) -> None:
        self.console.print(f"\n[bold {NOIR_ACCENT}]{title}[/bold {NOIR_ACCENT}]\n", justify="center")

    def show_analyzing(self, hints: list[str] | None = None) -> None:
        """Typing effect using provider-specific hints."""
        pool = hints if hints else ["Analyzing data..."]
        line = random.choice(pool)
        for ch in line:
            sys.stdout.write(ch)
            sys.stdout.flush()
            time.sleep(0.025)
        sys.stdout.write("\n\n")
        sys.stdout.flush()

    def show_question(self, q: BaseQuestion) -> None:
        media = q.media()
        if media:
            if media.type == MediaType.PHOTO_URL:
                try:
                    import requests
                    import base64
                    import os
                    self.console.print(f"[link={media.content}]Photo (Cmd+Click to open)[/link]")
                    resp = requests.get(media.content, timeout=5)
                    if resp.status_code == 200:
                        term_prog = os.environ.get("TERM_PROGRAM", "")
                        if term_prog in ("iTerm.app", "vscode", "WezTerm", "Ghostty") or "kitty" in os.environ.get("TERM", ""):
                            img_b64 = base64.b64encode(resp.content).decode("ascii")
                            sys.stdout.write(f"\033]1337;File=inline=1;height=12;preserveAspectRatio=1:{img_b64}\a\n")
                            sys.stdout.flush()
                        else:
                            from io import BytesIO
                            try:
                                from PIL import Image
                                from rich_pixels import Pixels
                                with Image.open(BytesIO(resp.content)) as image:
                                    image.thumbnail((60, 60))
                                    pixels = Pixels.from_image(image)
                                    self.console.print(pixels)
                            except ImportError:
                                self.console.print(f"[{NOIR_DIM}](Image rendering unavailable — install Pillow & rich-pixels)[/{NOIR_DIM}]")
                    else:
                        raise ValueError(f"HTTP {resp.status_code}")
                except Exception as e:
                    self.console.print(
                        Panel(f"\n[{NOIR_DIM}](Could not load image: {e})[/{NOIR_DIM}]", border_style=NOIR_BORDER, width=60)
                    )
            else:
                self.console.print(Panel(media.content, border_style=NOIR_BORDER, width=60))

        # Detective notebook panel for the question
        self.console.print(
            Panel(
                f"[bold white]{q.prompt_text()}[/bold white]",
                border_style=NOIR_BORDER,
                title=f"[{NOIR_DIM}]{self._s['analyzing']}[/{NOIR_DIM}]",
                expand=False,
            )
        )
        self.console.print()
        for i, choice in enumerate(q.choices(), 1):
            self.console.print(f"  [bold {NOIR_ACCENT}]{i}.[/bold {NOIR_ACCENT}] {choice}")
        self.console.print()

    def offer_hint(self, q: BaseQuestion) -> bool:
        """Ask if the user wants a hint. Returns True if hint was used."""
        ask = Prompt.ask(
            f"[{NOIR_DIM}]{self._s['hint_ask']}[/{NOIR_DIM}]",
            default="n",
        )
        if ask.strip().lower() in ("e", "evet", "y", "yes"):
            masked = _mask_answer(q.correct_answer)
            self.console.print(
                Panel(
                    f"[{NOIR_ACCENT}]{self._s['hint_label']} [bold]{masked}[/bold][/{NOIR_ACCENT}]",
                    border_style=NOIR_ACCENT,
                    expand=False,
                )
            )
            return True
        return False

    def get_answer(self, max_choices: int) -> int:
        while True:
            prompt = self._s["get_answer"].format(n=max_choices)
            ans = Prompt.ask(f"[{NOIR_ACCENT}]{prompt}[/{NOIR_ACCENT}]")
            if ans.isdigit() and 1 <= int(ans) <= max_choices:
                return int(ans)
            self.console.print(f"[red]{self._s['invalid']}[/red]")

    def show_result(self, is_correct: bool, correct: str, explanation: str) -> None:
        if is_correct:
            self.console.print(f"\n[bold green]{self._s['correct']}[/bold green] {explanation}")
        else:
            self.console.print(
                f"\n[bold red]{self._s['wrong']}[/bold red] "
                f"{self._s['right_answer']} [bold {NOIR_ACCENT}]{correct}[/bold {NOIR_ACCENT}].\n"
                f"[{NOIR_DIM}]{explanation}[/{NOIR_DIM}]"
            )
        time.sleep(2)
