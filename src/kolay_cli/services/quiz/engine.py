from __future__ import annotations
from dataclasses import dataclass

from .base import BaseQuestionProvider
from .state import QuizState
from .renderer import Renderer


@dataclass
class SessionResult:
    score: int
    total: int
    streak_updated: bool
    achievements_earned: list[str]


class QuizEngine:
    def __init__(self, provider: BaseQuestionProvider, renderer: Renderer, state: QuizState) -> None:
        self.provider = provider
        self.renderer = renderer
        self.state = state

    def play(self, num_questions: int = 5) -> SessionResult:
        questions = self.provider.generate(num_questions, set(self.state.seen_question_ids))

        if not questions:
            self.renderer.clear()
            self.renderer.show_title("Kolay Quiz")
            self.renderer.console.print("[yellow]Not enough data to start a quiz![/yellow]")
            return SessionResult(0, 0, False, [])

        score = 0

        for i, q in enumerate(questions, 1):
            self.renderer.clear()
            title = self.provider.name.replace("_", " ").title()
            self.renderer.show_title(f"Kolay Quiz: {title}")
            self.renderer.console.print(
                f"[grey62]Question {i} of {len(questions)}[/grey62]  Current score: [bold]{score}[/bold]\n"
            )

            self.renderer.show_question(q)
            ans_idx = self.renderer.get_answer(max_choices=len(q.choices()))

            selected_choice = q.choices()[ans_idx - 1]
            result = q.check_answer(selected_choice)

            if result.is_correct:
                score += 1

            self.renderer.show_result(result.is_correct, result.correct_answer, result.explanation)
            self.state.add_seen(q.id)

        streak_updated = self.state.update_streak()
        if score > self.state.high_score:
            self.state.high_score = score

        self.state.save()

        return SessionResult(
            score=score,
            total=len(questions),
            streak_updated=streak_updated,
            achievements_earned=[],
        )
