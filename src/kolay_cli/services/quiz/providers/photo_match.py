from __future__ import annotations
import random
from typing import Any

from ..base import BaseQuestionProvider, BaseQuestion, QuestionResult, QuestionMedia, MediaType


class PhotoMatchQuestion(BaseQuestion):
    def __init__(self, person: dict[str, Any], distractors: list[dict[str, Any]]) -> None:
        self.person = person
        self.distractors = distractors
        
        choices = [
            f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() 
            for p in [person] + distractors
        ]
        random.shuffle(choices)
        self._choices = choices
        self.correct_name = f"{person.get('firstName', '')} {person.get('lastName', '')}".strip()

    @property
    def id(self) -> str:
        return str(self.person.get("id", ""))

    def prompt_text(self) -> str:
        return "Who is this person?"

    def choices(self) -> list[str]:
        return self._choices

    @property
    def correct_answer(self) -> str:
        return self.correct_name

    def check_answer(self, answer: str) -> QuestionResult:
        is_correct = answer == self.correct_name
        dept = (self.person.get("department") or {}).get("name") or "Unknown department"
        # Include title if available
        title = self.person.get("title")
        if title:
            expl = f"{self.correct_name} works as {title} in {dept}."
        else:
            expl = f"{self.correct_name} works in {dept}."
            
        return QuestionResult(is_correct, self.correct_name, expl)

    def media(self) -> QuestionMedia | None:
        url = self.person.get("photoUrl") or self.person.get("avatarUrl")
        if url:
            return QuestionMedia(MediaType.PHOTO_URL, url)
        return None


class PhotoMatchProvider(BaseQuestionProvider):
    name = "photo_match"
    analyzing_hints = [
        "Scanning employee directory...",
        "Loading profile photos...",
        "Shuffling the faces...",
        "Who could this be?",
    ]

    def generate(self, count: int, seen_ids: set[str]) -> list[BaseQuestion]:
        all_people = self.data_provider.list_people(limit=100)
        
        # Valid pool: people with photos
        valid_pool = [p for p in all_people if p.get("photoUrl") or p.get("avatarUrl")]
        
        if not valid_pool:
            return []
            
        unseen = [p for p in valid_pool if str(p.get("id")) not in seen_ids]
        
        # Fallback to general pool if unseen runs out
        pool = unseen if len(unseen) >= count else valid_pool
        
        if len(pool) < count:
            count = len(pool)
            
        selected = random.sample(pool, count)
        questions: list[BaseQuestion] = []
        
        for p in selected:
            # Pick 3 distractors
            others = [x for x in all_people if x.get("id") != p.get("id")]
            if len(others) >= 3:
                distractors = random.sample(others, 3)
            else:
                distractors = others
            questions.append(PhotoMatchQuestion(p, distractors))
            seen_ids.add(str(p.get("id")))  # Prevent duplicates within the same round
            
        return questions
