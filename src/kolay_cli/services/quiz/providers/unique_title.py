"""Case: The Unique Title Hunt — Which job title is held by only one person?"""
from __future__ import annotations
import random
from collections import Counter
from typing import Any

from ..base import BaseQuestionProvider, BaseQuestion, QuestionResult, QuestionMedia


# We no longer need _flatten_titles since we use employee profiles directly.


class UniqueTitleQuestion(BaseQuestion):
    def __init__(self, unique_title: str, choices: list[str], fun_fact: str) -> None:
        self._unique_title = unique_title
        self._choices = choices
        self._fun_fact = fun_fact

    @property
    def id(self) -> str:
        return f"unique_title_{self._unique_title.lower().replace(' ', '_')[:30]}"

    def prompt_text(self) -> str:
        return (
            "Which job title is held by exactly one person in the company?\n"
            "   (Find the loneliest title in the org chart!)"
        )


    def choices(self) -> list[str]:
        return self._choices

    @property
    def correct_answer(self) -> str:
        return self._unique_title

    def check_answer(self, answer: str) -> QuestionResult:
        is_correct = answer.strip() == self._unique_title
        return QuestionResult(
            is_correct=is_correct,
            correct_answer=self._unique_title,
            explanation=self._fun_fact,
        )

    def media(self) -> QuestionMedia | None:
        return None


class UniqueTitleProvider(BaseQuestionProvider):
    name = "unique_title"
    analyzing_hints = [
        "Scanning the org chart...",
        "Counting job titles...",
        "Looking for the lonely ones...",
        "Inspecting position records...",
    ]

    def generate(self, count: int, seen_ids: set[str]) -> list[BaseQuestion]:
        all_people = self.data_provider.list_people(limit=200)
        titles = [p.get("title") for p in all_people if p.get("title")]

        if not titles:
            return []

        counts = Counter(titles)
        unique_titles = [t for t, c in counts.items() if c == 1]
        multi_titles = [t for t, c in counts.items() if c > 1]

        if not unique_titles or len(multi_titles) < 3:
            return []

        questions = []
        pool = list(unique_titles)
        random.shuffle(pool)

        for unique_title in pool[:count]:
            q_id = f"unique_title_{unique_title.lower().replace(' ', '_')[:30]}"
            if q_id in seen_ids:
                continue

            distractors = random.sample(multi_titles, min(3, len(multi_titles)))
            choices = [unique_title] + distractors
            random.shuffle(choices)

            fun_fact = (
                f"'{unique_title}' is a truly unique title — "
                f"only one person holds it in the entire company!"
            )

            questions.append(UniqueTitleQuestion(unique_title, choices, fun_fact))
            seen_ids.add(q_id)

        return questions
