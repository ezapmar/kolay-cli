"""Case: The Leave Time Machine — How many days off did we take in a random past month?

Generalized from 'December Exodus'. Now picks any month since the tenant was created,
so the question stays fresh and covers the company's full history.
"""
from __future__ import annotations
import calendar
import random
import unicodedata
from datetime import date
from typing import Any

from ..base import BaseQuestionProvider, BaseQuestion, QuestionResult, QuestionMedia

ANNUAL_LEAVE_KEYWORDS = {"yillik izin", "annual leave", "uzaktan calisma", "remote"}

MONTH_NAMES_EN = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def _normalize(s: str) -> str:
    """Normalize Turkish string: NFKD decomposition + remove combining marks."""
    decomposed = unicodedata.normalize("NFKD", s.lower())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.replace("\u0131", "i").replace("\u00fc", "u").replace("\u00f6", "o").replace("\u015f", "s").replace("\u00e7", "c").replace("\u011f", "g")


def _is_counted_leave(leave_type_name: str) -> bool:
    name = _normalize(leave_type_name or "")
    return any(k in name for k in ANNUAL_LEAVE_KEYWORDS)


def _all_available_months(start_date_str: str) -> list[tuple[int, int]]:
    """Return all (year, month) tuples from start_date to the last completed month."""
    today = date.today()
    # Last completed month: if today is Jan 2026 → Dec 2025
    if today.month == 1:
        last_year, last_month = today.year - 1, 12
    else:
        last_year, last_month = today.year, today.month - 1

    try:
        start = date.fromisoformat(start_date_str[:10])
    except (ValueError, TypeError):
        start = date(today.year - 3, 1, 1)

    months = []
    y, m = start.year, start.month
    while (y, m) <= (last_year, last_month):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


class LeaveTimeMachineQuestion(BaseQuestion):
    def __init__(
        self,
        real_days: int,
        choices: list[str],
        fun_fact: str,
        year: int,
        month: int,
    ) -> None:
        self._real_days = real_days
        self._choices = choices
        self._fun_fact = fun_fact
        self._year = year
        self._month = month

    @property
    def id(self) -> str:
        return f"leave_time_machine_{self._year}_{self._month:02d}"

    def prompt_text(self) -> str:
        month_name = MONTH_NAMES_EN.get(self._month, str(self._month))
        return (
            f"[QUIZ] In {month_name} {self._year}, how many person-days of annual leave\n"
            "   or remote work were recorded? (Guess the absentee tally!)"
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
    # Keep name "december_exodus" for backwards-compat with CLI mode selection
    name = "december_exodus"
    analyzing_hints = [
        "Consulting the leave ledger...",
        "Counting absent sunrises...",
        "Paging through time-off records...",
        "Tallying days away from the office...",
    ]

    def generate(self, count: int, seen_ids: set[str]) -> list[BaseQuestion]:
        # Get all available months from tenant inception to last completed month
        company_start = self.data_provider.get_company_start_date()
        all_months = _all_available_months(company_start)

        if not all_months:
            return []

        # Filter out already-seen months
        unseen = [
            (y, m) for y, m in all_months
            if f"leave_time_machine_{y}_{m:02d}" not in seen_ids
        ]

        if not unseen:
            return []

        # Weighted random: prefer recent months (more interesting data), but allow any
        # Simple weighting: last 24 months get 3× weight, rest get 1×
        today = date.today()
        cutoff = (today.year - 2, today.month)
        recent = [(y, m) for y, m in unseen if (y, m) >= cutoff]
        older = [(y, m) for y, m in unseen if (y, m) < cutoff]

        weighted_pool = (recent * 3 + older) if recent else older
        random.shuffle(weighted_pool)

        questions: list[BaseQuestion] = []

        for year, month in weighted_pool:
            if len(questions) >= count:
                break

            q_id = f"leave_time_machine_{year}_{month:02d}"
            if q_id in seen_ids:
                continue

            last_day = calendar.monthrange(year, month)[1]
            leaves = self.data_provider.list_leaves(
                start=f"{year}-{month:02d}-01",
                end=f"{year}-{month:02d}-{last_day:02d}",
                limit=500,
            )

            total_days = 0
            for leave in leaves:
                leave_type = (leave.get("leaveType") or {}).get("name") or ""
                if _is_counted_leave(leave_type):
                    day_count = leave.get("dayCount") or leave.get("totalDays") or 0
                    total_days += int(day_count)

            if total_days == 0:
                continue  # Skip months with no data; try next

            # Generate 3 plausible distractor numbers
            distractors: set[int] = set()
            for pct in [0.65, 1.35, 1.6]:
                d = max(1, round(total_days * pct))
                if d != total_days:
                    distractors.add(d)
            attempts = 0
            while len(distractors) < 3 and attempts < 50:
                offset = random.choice([-10, -7, -4, -2, 3, 5, 8, 12, 18])
                candidate = max(1, total_days + offset)
                if candidate != total_days:
                    distractors.add(candidate)
                attempts += 1

            distractor_list = random.sample(list(distractors), min(3, len(distractors)))
            choices = [str(total_days)] + [str(d) for d in distractor_list]
            random.shuffle(choices)

            month_name = MONTH_NAMES_EN.get(month, str(month))
            weeks = round(total_days / 5, 1)
            fun_fact = (
                f"In {month_name} {year}: {total_days} person-days of leave / remote work — "
                f"equivalent to {weeks} full working weeks!"
            )

            questions.append(LeaveTimeMachineQuestion(total_days, choices, fun_fact, year, month))
            seen_ids.add(q_id)

        return questions
