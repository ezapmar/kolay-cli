"""Slack Bolt app — Socket Mode entry point."""
from __future__ import annotations

import os

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .dispatcher import (
    dispatch,
    handle_leave_request_submission,
    handle_timelog_create_submission,
    LEAVE_REQUEST_CALLBACK,
    TIMELOG_CREATE_CALLBACK,
)
from .quiz import handle_mode_selection, handle_answer
from .modals import LEAVE_REQUEST_CALLBACK, TIMELOG_CREATE_CALLBACK  # re-import for registration


def create_app() -> App:
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("SLACK_BOT_TOKEN environment variable is not set.")

    app = App(token=bot_token)

    # ── /kolay slash command ──────────────────────────────────────────────────
    @app.command("/kolay")
    def kolay_command(ack, body, client):  # type: ignore[no-untyped-def]
        dispatch(body.get("text", ""), body, client, ack)

    # ── Modal submissions ─────────────────────────────────────────────────────
    @app.view(LEAVE_REQUEST_CALLBACK)
    def leave_modal_submit(ack, body, client):  # type: ignore[no-untyped-def]
        handle_leave_request_submission(ack, body, client)

    @app.view(TIMELOG_CREATE_CALLBACK)
    def timelog_modal_submit(ack, body, client):  # type: ignore[no-untyped-def]
        handle_timelog_create_submission(ack, body, client)

    # ── Quiz: mode picker buttons ──────────────────────────────────────────────
    @app.action({"action_id": lambda aid: aid.startswith("quiz_start_mode_")})
    def quiz_mode_button(ack, body, client):  # type: ignore[no-untyped-def]
        handle_mode_selection(ack, body, client)

    # ── Quiz: answer buttons ───────────────────────────────────────────────────
    @app.action({"action_id": lambda aid: aid.startswith("quiz_answer_")})
    def quiz_answer_button(ack, body, client):  # type: ignore[no-untyped-def]
        handle_answer(ack, body, client)

    return app


def main() -> None:
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        raise RuntimeError("SLACK_APP_TOKEN environment variable is not set.")

    app = create_app()
    handler = SocketModeHandler(app, app_token)
    print("⚡️ Kolay Slack bot is running via Socket Mode…")
    handler.start()


if __name__ == "__main__":
    main()
