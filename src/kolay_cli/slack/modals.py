"""Leave Request and Timelog Create modals."""
from __future__ import annotations

from typing import Any


# ── Leave Request ─────────────────────────────────────────────────────────────

LEAVE_REQUEST_CALLBACK = "kolay_leave_request"

# Common leave types — fetched dynamically from API at runtime; these are defaults
_LEAVE_TYPES = [
    {"text": {"type": "plain_text", "text": "Annual Leave"}, "value": "annual"},
    {"text": {"type": "plain_text", "text": "Sick Leave"}, "value": "sick"},
    {"text": {"type": "plain_text", "text": "Remote Work"}, "value": "remote"},
    {"text": {"type": "plain_text", "text": "Compensatory"}, "value": "compensatory"},
    {"text": {"type": "plain_text", "text": "Other"}, "value": "other"},
]


def build_leave_request_modal(
    trigger_id: str,  # noqa: ARG001 — passed through to views_open
    leave_type_options: list[dict] | None = None,
    metadata: str = "",
) -> dict[str, Any]:
    options = leave_type_options or _LEAVE_TYPES
    return {
        "type": "modal",
        "callback_id": LEAVE_REQUEST_CALLBACK,
        "private_metadata": metadata,
        "title": {"type": "plain_text", "text": "Request Leave"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "leave_type",
                "label": {"type": "plain_text", "text": "Leave Type"},
                "element": {
                    "type": "static_select",
                    "action_id": "leave_type_select",
                    "placeholder": {"type": "plain_text", "text": "Choose leave type"},
                    "options": options,
                },
            },
            {
                "type": "input",
                "block_id": "start_date",
                "label": {"type": "plain_text", "text": "Start Date"},
                "element": {"type": "datepicker", "action_id": "start_date_pick"},
            },
            {
                "type": "input",
                "block_id": "end_date",
                "label": {"type": "plain_text", "text": "End Date"},
                "element": {"type": "datepicker", "action_id": "end_date_pick"},
            },
            {
                "type": "input",
                "block_id": "comment",
                "optional": True,
                "label": {"type": "plain_text", "text": "Comment"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "comment_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Optional note…"},
                },
            },
        ],
    }


def extract_leave_request_values(body: dict[str, Any]) -> dict[str, Any]:
    """Pull submitted values out of a view submission body."""
    vals = body["view"]["state"]["values"]
    leave_type = vals["leave_type"]["leave_type_select"]["selected_option"]["value"]
    start = vals["start_date"]["start_date_pick"]["selected_date"]
    end = vals["end_date"]["end_date_pick"]["selected_date"]
    comment = (vals.get("comment", {}).get("comment_input") or {}).get("value") or ""
    return {"leave_type": leave_type, "start_date": start, "end_date": end, "comment": comment}


# ── Timelog Create ────────────────────────────────────────────────────────────

TIMELOG_CREATE_CALLBACK = "kolay_timelog_create"

_TIMELOG_TYPES = [
    {"text": {"type": "plain_text", "text": "Work"}, "value": "work"},
    {"text": {"type": "plain_text", "text": "Break"}, "value": "break"},
    {"text": {"type": "plain_text", "text": "Overtime"}, "value": "overtime"},
]


def build_timelog_create_modal(metadata: str = "") -> dict[str, Any]:
    return {
        "type": "modal",
        "callback_id": TIMELOG_CREATE_CALLBACK,
        "private_metadata": metadata,
        "title": {"type": "plain_text", "text": "Log Time"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "person",
                "label": {"type": "plain_text", "text": "Employee Name or ID"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "person_input",
                    "placeholder": {"type": "plain_text", "text": "e.g. Tunca Üçer"},
                },
            },
            {
                "type": "input",
                "block_id": "start_date",
                "label": {"type": "plain_text", "text": "Start Date"},
                "element": {"type": "datepicker", "action_id": "start_date_pick"},
            },
            {
                "type": "input",
                "block_id": "end_date",
                "label": {"type": "plain_text", "text": "End Date"},
                "element": {"type": "datepicker", "action_id": "end_date_pick"},
            },
            {
                "type": "input",
                "block_id": "log_type",
                "label": {"type": "plain_text", "text": "Type"},
                "element": {
                    "type": "static_select",
                    "action_id": "log_type_select",
                    "options": _TIMELOG_TYPES,
                    "initial_option": _TIMELOG_TYPES[0],
                },
            },
            {
                "type": "input",
                "block_id": "description",
                "optional": True,
                "label": {"type": "plain_text", "text": "Description"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "description_input",
                    "placeholder": {"type": "plain_text", "text": "Optional…"},
                },
            },
        ],
    }


def extract_timelog_create_values(body: dict[str, Any]) -> dict[str, Any]:
    vals = body["view"]["state"]["values"]
    person = vals["person"]["person_input"]["value"]
    start = vals["start_date"]["start_date_pick"]["selected_date"]
    end = vals["end_date"]["end_date_pick"]["selected_date"]
    log_type = vals["log_type"]["log_type_select"]["selected_option"]["value"]
    desc = (vals.get("description", {}).get("description_input") or {}).get("value") or ""
    return {"person": person, "start_date": start, "end_date": end, "type": log_type, "description": desc}


# ── Settings (access control) ────────────────────────────────────────────────

SETTINGS_CALLBACK = "kolay_settings"


def build_settings_modal(
    current_channels: str = "",
    current_users: str = "",
    team_id: str = "",
) -> dict[str, Any]:
    return {
        "type": "modal",
        "callback_id": SETTINGS_CALLBACK,
        "private_metadata": team_id,
        "title": {"type": "plain_text", "text": "Kolay Settings"},
        "submit": {"type": "plain_text", "text": "Save"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Access Control (Option C)*\n"
                        "Set both fields to restrict `/kolay` to specific channels and users.\n"
                        "Leave both empty to allow everyone."
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "allowed_channels",
                "optional": True,
                "label": {"type": "plain_text", "text": "Allowed Channel IDs"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "channels_input",
                    "placeholder": {"type": "plain_text", "text": "C0123ABC, C0456DEF"},
                    **({"initial_value": current_channels} if current_channels else {}),
                },
            },
            {
                "type": "input",
                "block_id": "allowed_users",
                "optional": True,
                "label": {"type": "plain_text", "text": "Allowed User IDs"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "users_input",
                    "placeholder": {"type": "plain_text", "text": "U0123456, U0654321"},
                    **({"initial_value": current_users} if current_users else {}),
                },
            },
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "kolay_token",
                "optional": True,
                "label": {"type": "plain_text", "text": "Kolay API Token (update)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "token_input",
                    "placeholder": {"type": "plain_text", "text": "Leave empty to keep current token"},
                },
            },
        ],
    }


def extract_settings_values(body: dict[str, Any]) -> dict[str, Any]:
    vals = body["view"]["state"]["values"]
    channels = (vals.get("allowed_channels", {}).get("channels_input") or {}).get("value") or ""
    users = (vals.get("allowed_users", {}).get("users_input") or {}).get("value") or ""
    token = (vals.get("kolay_token", {}).get("token_input") or {}).get("value") or ""
    team_id = body["view"].get("private_metadata", "")
    return {
        "allowed_channels": channels.strip(),
        "allowed_users": users.strip(),
        "kolay_api_token": token.strip(),
        "team_id": team_id,
    }

