"""Interactive Slack quiz powered by the existing QuizEngine providers."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from ..services.quiz.base import BaseQuestion
from ..services.quiz.data_provider import KolayAPIProvider
from ..services.quiz import get_factory

_SESSION_TTL = 600  # seconds (10 min)

_MODE_LABELS: dict[str, str] = {
    "photo_match": "🖼️  Face ID",
    "education_champion": "🎓 Academic Degrees",
    "unique_title": "🏆 Lonely Roles",
    "december_exodus": "⏳ Leave Time Machine",
}

# Rank badge mapping (mirrors badges.py thresholds)
_RANK_EMOJIS = {
    "Cadet": "🔵",
    "Analyst": "🟢",
    "Investigator": "🟡",
    "Detective": "🟠",
    "Chief Inspector": "🔴",
    "Legend": "🟣",
}


@dataclass
class QuizSession:
    user_id: str
    channel_id: str
    mode: str
    questions: list[BaseQuestion]
    current_idx: int = 0
    score: int = 0
    started_at: float = field(default_factory=time.monotonic)

    def is_expired(self) -> bool:
        return (time.monotonic() - self.started_at) > _SESSION_TTL

    def is_done(self) -> bool:
        return self.current_idx >= len(self.questions)

    def current_question(self) -> BaseQuestion:
        return self.questions[self.current_idx]


# In-memory store: session_key → QuizSession
_sessions: dict[str, QuizSession] = {}


def _session_key(user_id: str, channel_id: str) -> str:
    return f"{user_id}:{channel_id}"


def _session_hash(user_id: str, channel_id: str) -> str:
    """Short hash used in action_ids to tie button clicks to a session."""
    return hashlib.md5(f"{user_id}{channel_id}".encode()).hexdigest()[:8]  # noqa: S324


def _purge_expired() -> None:
    expired = [k for k, s in _sessions.items() if s.is_expired()]
    for k in expired:
        del _sessions[k]


def _post(client: Any, user_id: Any, channel_id: str, **kwargs: Any) -> None:
    """Post a message: try channel first, fallback to DM (user_id as channel)."""
    try:
        client.chat_postMessage(channel=channel_id, **kwargs)
    except Exception as e1:
        print(f"[quiz._post] channel={channel_id} failed: {e1}", flush=True)
        try:
            client.chat_postMessage(channel=user_id, **kwargs)
        except Exception as e2:
            print(f"[quiz._post] DM user={user_id} failed: {e2}", flush=True)


# ── Block builders ─────────────────────────────────────────────────────────────

def build_mode_picker_blocks() -> list[dict]:
    """Mode selection — 4 buttons, one per quiz mode."""
    buttons = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": label, "emoji": True},
            "action_id": f"quiz_start_mode_{mode}",
            "value": mode,
        }
        for mode, label in _MODE_LABELS.items()
    ]
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*🔍 Data Detective* — choose your case:"},
        },
        {"type": "actions", "elements": buttons},
    ]


def build_question_blocks(
    q: BaseQuestion,
    idx: int,
    total: int,
    score: int,
    session_hash: str,
) -> list[dict]:
    choices = q.choices()
    buttons = []
    for ci, choice in enumerate(choices):
        buttons.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": choice[:75], "emoji": True},
                "action_id": f"quiz_answer_{session_hash}_{idx}_{ci}",
                "value": str(ci),
            }
        )
    return [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Question {idx + 1} of {total}  |  Score: {score}*\n\n"
                    f"{q.prompt_text()}"
                ),
            },
        },
        {"type": "actions", "elements": buttons},
    ]


def build_summary_blocks(session: QuizSession) -> list[dict]:
    total = len(session.questions)
    pct = int(session.score / total * 100) if total else 0
    rank = "Detective"
    if pct >= 90:
        rank = "Legend"
    elif pct >= 75:
        rank = "Chief Inspector"
    elif pct >= 60:
        rank = "Investigator"
    elif pct >= 40:
        rank = "Analyst"
    elif pct >= 20:
        rank = "Cadet"

    badge = _RANK_EMOJIS.get(rank, "🔵")
    verdict = ":trophy:" if pct >= 80 else (":chart_with_upwards_trend:" if pct >= 50 else ":bulb:")
    return [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{verdict} *Case Closed!*\n\n"
                    f"*Score:* {session.score}/{total} ({pct}%)\n"
                    f"*Rank:* {badge} {rank}\n"
                    f"*Mode:* {_MODE_LABELS.get(session.mode, session.mode)}\n\n"
                    f"Run `/kolaycli quiz` to start a new case."
                ),
            },
        },
    ]


def build_answer_result_blocks(
    q: BaseQuestion,
    chosen_answer: str,
    idx: int,
    total: int,
    score: int,
) -> list[dict]:
    result = q.check_answer(chosen_answer)
    icon = ":white_check_mark:" if result.is_correct else ":x:"
    return [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Q{idx + 1} of {total}*  {icon}\n"
                    f"*Answer:* {result.correct_answer}\n"
                    f"_{result.explanation}_"
                ),
            },
        },
    ]


# ── Public handlers (called from app.py) ──────────────────────────────────────

def handle_quiz_command(ack: Any, body: Any, client: Any, respond: Any = None) -> None:
    """Handle /kolay quiz — show the mode picker."""
    ack()
    _purge_expired()
    blocks = build_mode_picker_blocks()
    if respond:
        respond(text="Data Detective — choose your case", blocks=blocks, response_type="ephemeral")
    else:
        channel = body.get("channel_id") or body.get("channel", {}).get("id", "")
        client.chat_postEphemeral(
            channel=channel,
            user=body["user_id"],
            blocks=blocks,
            text="Data Detective — choose your case",
        )


def handle_mode_selection(ack: Any, body: Any, client: Any) -> None:
    """Handle the mode button click — generate questions and post Q1."""
    ack()
    _purge_expired()

    action = body["actions"][0]
    mode = action["value"]
    user_id = body["user"]["id"]
    channel_id = (body.get("channel") or {}).get("id", user_id)
    key = _session_key(user_id, channel_id)
    print(f"[quiz] mode={mode} user={user_id} channel={channel_id}", flush=True)

    # Generate questions
    try:
        provider = get_factory().get_provider(mode, KolayAPIProvider())
        questions = provider.generate(5, set())
        print(f"[quiz] generated {len(questions)} questions", flush=True)
    except Exception as exc:
        print(f"[quiz] generate failed: {exc}", flush=True)
        _post(client, user_id, channel_id, text=f":x: Could not load questions: {exc}")
        return

    if not questions:
        _post(client, user_id, channel_id, text=":warning: Not enough data for this mode. Try another!")
        return

    session = QuizSession(
        user_id=user_id,
        channel_id=channel_id,
        mode=mode,
        questions=questions,
    )
    _sessions[key] = session

    sh = _session_hash(user_id, channel_id)
    _post(
        client, user_id, channel_id,
        blocks=build_question_blocks(questions[0], 0, len(questions), 0, sh),
        text=f"Data Detective — Q1 of {len(questions)}",
    )


def handle_answer(ack: Any, body: Any, client: Any) -> None:
    """Handle an answer button click."""
    ack()

    action = body["actions"][0]
    user_id = body["user"]["id"]
    channel_id = (body.get("channel") or {}).get("id", user_id)
    key = _session_key(user_id, channel_id)

    session = _sessions.get(key)
    if not session or session.is_expired():
        _post(client, user_id, channel_id, text=":hourglass: Session expired. Run `/kolaycli quiz` to start again.")
        return

    # Decode chosen_index from action_id: quiz_answer_{hash}_{qidx}_{cidx}
    parts = action["action_id"].split("_")
    try:
        q_idx = int(parts[-2])
        c_idx = int(parts[-1])
    except (ValueError, IndexError):
        return

    # Guard against duplicate/stale button presses
    if q_idx != session.current_idx:
        return

    q = session.current_question()
    choices = q.choices()
    chosen = choices[c_idx] if c_idx < len(choices) else ""

    result = q.check_answer(chosen)
    if result.is_correct:
        session.score += 1

    # Post the result feedback
    result_blocks = build_answer_result_blocks(
        q, chosen, session.current_idx, len(session.questions), session.score
    )
    _post(client, user_id, channel_id, blocks=result_blocks, text="Answer result")

    session.current_idx += 1

    if session.is_done():
        # Post summary
        _post(client, user_id, channel_id, blocks=build_summary_blocks(session), text="Quiz complete!")
        del _sessions[key]
    else:
        # Post next question
        sh = _session_hash(user_id, channel_id)
        nq = session.current_question()
        _post(
            client, user_id, channel_id,
            blocks=build_question_blocks(
                nq, session.current_idx, len(session.questions), session.score, sh
            ),
            text=f"Question {session.current_idx + 1}",
        )
