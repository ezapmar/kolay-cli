"""Tests for the Slack integration layer (no real Slack API calls)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ── Formatter tests ───────────────────────────────────────────────────────────

def test_dict_to_fields_basic():
    from kolay_cli.slack.formatters import dict_to_fields
    blocks = dict_to_fields({"name": "Alice", "title": "Engineer"}, ["name", "title"])
    assert len(blocks) == 1
    assert blocks[0]["type"] == "section"
    fields = blocks[0]["fields"]
    assert any("Alice" in f["text"] for f in fields)


def test_list_to_blocks():
    from kolay_cli.slack.formatters import list_to_blocks
    items = [{"name": "Alice", "title": "Eng"}, {"name": "Bob", "title": "PM"}]
    blocks = list_to_blocks(items, ["name", "title"], "Employees")
    types = [b["type"] for b in blocks]
    assert "header" in types
    assert "section" in types


def test_error_block():
    from kolay_cli.slack.formatters import error_block
    b = error_block("Something went wrong")
    assert b[0]["type"] == "section"
    assert ":x:" in b[0]["text"]["text"]


def test_overflow_to_csv():
    from kolay_cli.slack.formatters import overflow_to_csv
    items = [{"name": "Alice", "dept": "Eng"}, {"name": "Bob", "dept": "PM"}]
    result = overflow_to_csv(items)
    assert b"Alice" in result
    assert b"name" in result  # header row


# ── Dispatcher parse tests ────────────────────────────────────────────────────

def test_dispatcher_parse_help():
    from kolay_cli.slack.dispatcher import _parse
    assert _parse("help") == ("help", "", [])
    assert _parse("") == ("help", "", [])


def test_dispatcher_parse_person_list():
    from kolay_cli.slack.dispatcher import _parse
    m, a, r = _parse("person list --search Alice")
    assert m == "person"
    assert a == "list"
    assert "--search" in r


def test_dispatcher_parse_leave_request():
    from kolay_cli.slack.dispatcher import _parse
    m, a, _ = _parse("leave request")
    assert m == "leave"
    assert a == "request"


def test_dispatcher_parse_quiz():
    from kolay_cli.slack.dispatcher import _parse
    m, a, _ = _parse("quiz")
    assert m == "quiz"


# ── Modal structure tests ─────────────────────────────────────────────────────

def test_leave_modal_structure():
    from kolay_cli.slack.modals import build_leave_request_modal
    view = build_leave_request_modal("dummy_trigger")
    assert view["type"] == "modal"
    assert view["callback_id"] == "kolay_leave_request"
    block_ids = [b.get("block_id") for b in view["blocks"]]
    assert "leave_type" in block_ids
    assert "start_date" in block_ids
    assert "end_date" in block_ids


def test_timelog_modal_structure():
    from kolay_cli.slack.modals import build_timelog_create_modal
    view = build_timelog_create_modal()
    assert view["type"] == "modal"
    assert view["callback_id"] == "kolay_timelog_create"
    block_ids = [b.get("block_id") for b in view["blocks"]]
    assert "person" in block_ids
    assert "log_type" in block_ids


# ── Quiz session tests ────────────────────────────────────────────────────────

def test_quiz_mode_picker_blocks():
    from kolay_cli.slack.quiz import build_mode_picker_blocks
    blocks = build_mode_picker_blocks()
    assert any(b["type"] == "actions" for b in blocks)
    action_block = next(b for b in blocks if b["type"] == "actions")
    assert len(action_block["elements"]) == 4
    action_ids = [e["action_id"] for e in action_block["elements"]]
    assert any("quiz_start_mode_" in aid for aid in action_ids)


def test_quiz_question_blocks_has_4_buttons():
    from kolay_cli.slack.quiz import build_question_blocks
    from kolay_cli.services.quiz.providers.unique_title import UniqueTitleQuestion

    q = UniqueTitleQuestion(
        unique_title="CEO",
        choices=["CEO", "Director", "Manager", "Analyst"],
        fun_fact="Only one CEO exists.",
    )
    blocks = build_question_blocks(q, idx=0, total=5, score=0, session_hash="abc12345")
    actions = next(b for b in blocks if b["type"] == "actions")
    assert len(actions["elements"]) == 4


def test_quiz_session_lifecycle():
    from kolay_cli.slack.quiz import _sessions, _session_key, QuizSession
    from kolay_cli.services.quiz.providers.unique_title import UniqueTitleQuestion

    key = _session_key("U_test", "C_test")
    q = UniqueTitleQuestion("CEO", ["CEO", "Dir", "Mgr", "Eng"], "CEO is unique.")
    session = QuizSession(user_id="U_test", channel_id="C_test", mode="unique_title", questions=[q])
    _sessions[key] = session

    assert not session.is_done()
    q_obj = session.current_question()
    result = q_obj.check_answer("CEO")
    assert result.is_correct
    session.score += 1
    session.current_idx += 1
    assert session.is_done()

    # cleanup
    del _sessions[key]


def test_quiz_session_expiry():
    from kolay_cli.slack.quiz import _sessions, _session_key, QuizSession, _purge_expired
    from kolay_cli.services.quiz.providers.unique_title import UniqueTitleQuestion
    import time

    key = _session_key("U_expire", "C_expire")
    q = UniqueTitleQuestion("X", ["X", "Y", "Z", "W"], "fact")
    session = QuizSession(user_id="U_expire", channel_id="C_expire",
                          mode="unique_title", questions=[q])
    # Force it to look expired
    session.started_at = time.monotonic() - 700
    _sessions[key] = session

    assert session.is_expired()
    _purge_expired()
    assert key not in _sessions
