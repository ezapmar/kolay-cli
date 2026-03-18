"""Case: The December Exodus — How many sunrises did we miss last December?"""
from __future__ import annotations
import random
import unicodedata
from datetime import date
from typing import Any

from ..base import BaseQuestionProvider, BaseQuestion, QuestionResult, QuestionMedia

ANNUAL_LEAVE_KEYWORDS = {"yillik izin", "annual leave", "uzaktan calisma", "remote"}


def _normalize(s: str) -> str:
    """Normalize Turkish string: decompose Unicode, remove combining marks, then replace chars."""
    # NFKD decomposes İ (U+0130) into i + combining dot above, then we strip combining marks
    decomposed = unicodedata.normalize("NFKD", s.lower())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    # Also swap dotless-ı and other chars that survive
    return stripped.replace("\u0131", "i").replace("\u00fc", "u").replace("\u00f6", "o").replace("\u015f", "s").replace("\u00e7", "c").replace("\u011f", "g")


def _is_counted_leave(leave_type_name: str) -> bool:
    name = _normalize(leave_type_name or "")
    return any(k in name for k in ANNUAL_LEAVE_KEYWORDS)


class DecemberExodusQuestion(BaseQuestion):
    def __init__(self, real_days: int, choices: list[str], fun_fact: str, year: int) -> None:
        self._real_days = real_days
        self._choices = choices
        self._fun_fact = fun_fact
        self._year = year

    @property
    def id(self) -> str:
        return f"december_exodus_{self._year}"

    def prompt_text(self) -> str:
        return (
            f"🌅 {self._year} Aralık'ında kaç kişi-günlük yıllık izin / uzaktan çalışma kullanıldı?\n"
            "   (Aralık ayında 'kaybolan' güneş doğuşlarını tahmin edin!)"
        )

    def choices(self) -> list[str]:
        return self._choices

    @property
    def correct_answer(self) -> str:
        return str(self._real_days)

    def check_answer(self, answer: str) -> QuestionResult:
        is_correct = answer.strip() == str(self._real_days)
        return QuestionResult(
            is_correct=is_correct,
            correct_answer=str(self._real_days),
            explanation=self._fun_fact,
        )

    def media(self) -> QuestionMedia | None:
        return None


class DecemberExodusProvider(BaseQuestionProvider):
    name = "december_exodus"

    def generate(self, count: int, seen_ids: set[str]) -> list[BaseQuestion]:
        # Use previous December
        today = date.today()
        target_year = today.year - 1 if today.month < 12 else today.year

        q_id = f"december_exodus_{target_year}"
        if q_id in seen_ids:
            return []

        leaves = self.data_provider.list_leaves(
            start=f"{target_year}-12-01",
            end=f"{target_year}-12-31",
            limit=500,
        )

        total_days = 0
        for leave in leaves:
            leave_type = (leave.get("leaveType") or {}).get("name") or ""
            if _is_counted_leave(leave_type):
                day_count = leave.get("dayCount") or leave.get("totalDays") or 0
                total_days += int(day_count)

        if total_days == 0:
            return []

        # Generate 3 plausible distractor numbers
        distractors = set()
        for pct in [0.7, 1.3, 1.5]:
            d = max(1, round(total_days * pct))
            if d != total_days:
                distractors.add(d)
        while len(distractors) < 3:
            offset = random.choice([-5, -3, 5, 8, 10, 15])
            candidate = max(1, total_days + offset)
            if candidate != total_days:
                distractors.add(candidate)

        distractor_list = random.sample(list(distractors), 3)
        choices = [str(total_days)] + [str(d) for d in distractor_list]
        random.shuffle(choices)

        weeks = round(total_days / 5, 1)
        fun_fact = (
            f"{target_year} Aralık'ında toplam {total_days} kişi-günlük yıllık izin / "
            f"uzaktan çalışma kullanıldı. Bu, {weeks} haftalık tam çalışma süresine eşdeğer!"
        )

        return [DecemberExodusQuestion(total_days, choices, fun_fact, target_year)]
