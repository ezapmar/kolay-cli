from __future__ import annotations
from dataclasses import dataclass, field

from .base import BaseQuestionProvider
from .state import QuizState
from .renderer import Renderer


STREAK_BADGE_MILESTONES = {5, 10, 25, 50}

POINTS_CORRECT = 10
POINTS_NO_HINT_BONUS = 5
POINTS_HINT_PENALTY = -3

_TITLE_LABELS = {
    "en": "Data Detective",
    "tr": "Veri Dedektifi",
}
_NO_DATA_LABELS = {
    "en": "Not enough data to start a session. Try again later.",
    "tr": "Yeterli veri bulunamadı. Lütfen daha sonra tekrar deneyin.",
}
_CASE_LABELS = {
    "en": "Case",
    "tr": "Dava",
}
_TOTAL_LABELS = {
    "en": "Total",
    "tr": "Toplam",
}
_SCORE_LABELS = {
    "en": "Score",
    "tr": "Puan",
}


@dataclass
class SessionResult:
    score: int
    total: int
    points_earned: int
    streak_updated: bool
    achievements_earned: list[str] = field(default_factory=list)


class QuizEngine:
    def __init__(
        self,
        provider: BaseQuestionProvider,
        renderer: Renderer,
        state: QuizState,
        hints_enabled: bool = True,
        lang: str = "en",
    ) -> None:
        self.provider = provider
        self.renderer = renderer
        self.state = state
        self.hints_enabled = hints_enabled
        self.lang = lang

    def play(self, num_questions: int = 5) -> SessionResult:
        questions = self.provider.generate(num_questions, set(self.state.seen_question_ids))

        if not questions:
            self.renderer.clear()
            title_label = _TITLE_LABELS.get(self.lang, "Data Detective")
            self.renderer.show_title(f"🔍 {title_label}")
            self.renderer.console.print(f"[yellow]{_NO_DATA_LABELS.get(self.lang, '')}[/yellow]")
            return SessionResult(0, 0, 0, False)

        score = 0
        session_points = 0
        case_label = _CASE_LABELS.get(self.lang, "Case")
        score_label = _SCORE_LABELS.get(self.lang, "Score")
        total_label = _TOTAL_LABELS.get(self.lang, "Total")
        title_label = _TITLE_LABELS.get(self.lang, "Data Detective")

        for i, q in enumerate(questions, 1):
            self.renderer.clear()
            mode_title = self.provider.name.replace("_", " ").title()
            self.renderer.show_title(f"🔍 {title_label} — {mode_title}")
            self.renderer.console.print(
                f"[grey62]{case_label} {i} / {len(questions)}[/grey62]  "
                f"{score_label}: [bold]{score}[/bold]  "
                f"{total_label}: [bold yellow]{self.state.total_case_points + session_points}[/bold yellow]\n"
            )

            # Use the provider's context-specific analyzing hints
            self.renderer.show_analyzing(hints=self.provider.analyzing_hints)
            self.renderer.show_question(q)

            hint_used = False
            if self.hints_enabled:
                hint_used = self.renderer.offer_hint(q)
                if hint_used:
                    self.state.hints_used += 1

            ans_idx = self.renderer.get_answer(max_choices=len(q.choices()))
            selected_choice = q.choices()[ans_idx - 1]
            result = q.check_answer(selected_choice)

            if result.is_correct:
                score += 1
                pts = POINTS_CORRECT
                if not hint_used:
                    pts += POINTS_NO_HINT_BONUS
                session_points += pts
            else:
                if hint_used:
                    session_points += POINTS_HINT_PENALTY

            self.renderer.show_result(result.is_correct, result.correct_answer, result.explanation)
            self.state.add_seen(q.id)

        # Persist session
        self.state.add_points(session_points)
        streak_updated = self.state.update_streak()
        if score > self.state.high_score:
            self.state.high_score = score
        self.state.save()

        # Badge milestone check
        if streak_updated and self.state.current_streak in STREAK_BADGE_MILESTONES:
            from .badges import render_streak_badge
            render_streak_badge(self.renderer.console, self.state.current_streak, self.state.rank)

        return SessionResult(
            score=score,
            total=len(questions),
            points_earned=session_points,
            streak_updated=streak_updated,
            achievements_earned=[],
        )
