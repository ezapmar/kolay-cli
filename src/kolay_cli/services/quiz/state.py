from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta


@dataclass
class QuizState:
    high_score: int = 0
    current_streak: int = 0
    last_played: str | None = None  # YYYY-MM-DD
    seen_question_ids: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)

    @classmethod
    def load(cls) -> QuizState:
        path = cls._get_path()
        if not path.exists():
            return cls()
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except Exception:
            return cls()

    def save(self) -> None:
        path = self._get_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    def update_streak(self) -> bool:
        """Returns True if streak was incremented."""
        today = date.today().isoformat()
        if not self.last_played:
            self.current_streak = 1
            self.last_played = today
            return True

        last_played_date = date.fromisoformat(self.last_played)
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        if self.last_played == yesterday:
            self.current_streak += 1
            self.last_played = today
            return True
        elif self.last_played == today:
            return False  # Already played today
        else:
            # Streak broken
            self.current_streak = 1
            self.last_played = today
            return True

    def add_seen(self, q_id: str) -> None:
        if q_id not in self.seen_question_ids:
            self.seen_question_ids.append(q_id)
            # keep array bounded somewhat
            if len(self.seen_question_ids) > 1000:
                self.seen_question_ids = self.seen_question_ids[-1000:]

    @classmethod
    def _get_path(cls) -> Path:
        return Path.home() / ".config" / "kolay" / "quiz_state.json"
