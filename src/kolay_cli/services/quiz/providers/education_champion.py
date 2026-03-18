"""Case: The Education Champion — Which department is the local Think-Tank?"""
from __future__ import annotations
import random
import unicodedata
from collections import defaultdict
from typing import Any

from ..base import BaseQuestionProvider, BaseQuestion, QuestionResult, QuestionMedia


# Normalized (ASCII-safe) postgraduate keywords
POSTGRAD_KEYWORDS = {
    "yuksek lisans",
    "lisans ustu",
    "doktora",
    "master", "masters",
    "phd",
    "mba",
}


def _tr_normalize(s: str) -> str:
    """Normalize Turkish string to plain ASCII-ish for reliable substring matching."""
    decomposed = unicodedata.normalize("NFKD", s.lower())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.replace("\u0131", "i").replace("\u00fc", "u").replace("\u00f6", "o").replace("\u015f", "s").replace("\u00e7", "c").replace("\u011f", "g")


def _is_postgrad(level: str) -> bool:
    normalized = _tr_normalize(level)
    return any(k in normalized for k in POSTGRAD_KEYWORDS)


class EducationChampionQuestion(BaseQuestion):
    def __init__(
        self,
        winner_dept: str,
        winner_pct: float,
        choices: list[str],
        fun_fact: str,
    ) -> None:
        self._winner = winner_dept
        self._winner_pct = winner_pct
        self._choices = choices
        self._fun_fact = fun_fact

    @property
    def id(self) -> str:
        return f"edu_champ_{self._winner.lower().replace(' ', '_')}"

    def prompt_text(self) -> str:
        return "🎓 Hangi departman şirketin lokal 'Think-Tank'ı?\n   (Lisansüstü mezun yüzdesi en yüksek departman)"

    def choices(self) -> list[str]:
        return self._choices

    @property
    def correct_answer(self) -> str:
        return self._winner

    def check_answer(self, answer: str) -> QuestionResult:
        is_correct = answer.strip() == self._winner
        return QuestionResult(
            is_correct=is_correct,
            correct_answer=self._winner,
            explanation=self._fun_fact,
        )

    def media(self) -> QuestionMedia | None:
        return None


class EducationChampionProvider(BaseQuestionProvider):
    name = "education_champion"

    def generate(self, count: int, seen_ids: set[str]) -> list[BaseQuestion]:
        people = self.data_provider.list_people(limit=200)
        if not people:
            return []

        dept_total: dict[str, int] = defaultdict(int)
        dept_postgrad: dict[str, int] = defaultdict(int)

        for p in people:
            dept = (p.get("department") or {}).get("name") or "Bilinmiyor"
            level = p.get("educationLevel") or ""
            dept_total[dept] += 1
            if _is_postgrad(level):
                dept_postgrad[dept] += 1

        # All departments with at least 1 person are eligible; need at least 2 distinct depts for choices
        eligible = {d: dept_postgrad[d] / dept_total[d] for d in dept_total}
        if len(eligible) < 2:
            return []

        sorted_depts = sorted(eligible.items(), key=lambda x: x[1], reverse=True)
        winner_dept, winner_ratio = sorted_depts[0]
        winner_pct = round(winner_ratio * 100)

        q_id = f"edu_champ_{winner_dept.lower().replace(' ', '_')}"
        if q_id in seen_ids:
            return []

        # Build 3 distractor departments
        distractors = [d for d, _ in sorted_depts[1:4]]
        while len(distractors) < 3:
            distractors.append(f"Departman {len(distractors)+1}")

        choices = [winner_dept] + distractors[:3]
        random.shuffle(choices)

        fun_fact = (
            f"{winner_dept} departmanı %{winner_pct} lisansüstü oranıyla "
            f"şirketin akademik gücünü temsil ediyor!"
        )

        return [EducationChampionQuestion(winner_dept, winner_ratio, choices, fun_fact)]
