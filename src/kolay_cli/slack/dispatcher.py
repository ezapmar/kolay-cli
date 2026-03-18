"""Command dispatcher: parses /kolay <text> and routes to service functions."""
from __future__ import annotations

import shlex
from typing import Any

from ..services import (
    person as person_svc,
    leave as leave_svc,
    timelog as timelog_svc,
    unit as unit_svc,
    approval as approval_svc,
)
from .formatters import (
    dict_to_fields,
    list_to_blocks,
    error_block,
    render_text,
    overflow_to_csv,
)
from .modals import (
    build_leave_request_modal,
    extract_leave_request_values,
    build_timelog_create_modal,
    extract_timelog_create_values,
    build_settings_modal,
    extract_settings_values,
    LEAVE_REQUEST_CALLBACK,
    TIMELOG_CREATE_CALLBACK,
    SETTINGS_CALLBACK,
)

# ── Help card ─────────────────────────────────────────────────────────────────

_HELP_BLOCKS: list[dict] = [
    {
        "type": "header",
        "text": {"type": "plain_text", "text": "🔷 Kolay IK — Slack Commands", "emoji": True},
    },
    {"type": "divider"},
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                "*People*\n"
                "`/kolaycli person list [--search NAME]`  — list active employees\n"
                "`/kolaycli person view ID_OR_NAME`  — full profile\n"
                "`/kolaycli person leave-status ID`  — leave balances\n\n"
                "*Leave*\n"
                "`/kolaycli leave list`  — this year's leaves\n"
                "`/kolaycli leave view ID`  — single leave record\n"
                "`/kolaycli leave request`  — 📋 open request modal\n\n"
                "*Timelog*\n"
                "`/kolaycli timelog list`  — recent time logs\n"
                "`/kolaycli timelog create`  — 📋 open create modal\n\n"
                "*Organization*\n"
                "`/kolaycli unit tree`  — org chart snapshot\n"
                "`/kolaycli approval list`  — approval processes\n\n"
                "*Quiz*\n"
                "`/kolaycli quiz`  — 🎮 start Data Detective\n"
                "`/kolaycli quiz --mode unique_title`  — skip mode picker\n\n"
                "*Admin*\n"
                "`/kolaycli settings`  — ⚙️ update access restrictions & API token\n\n"
                "`/kolaycli help`  — show this message"
            ),
        },
    },
]


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse(text: str) -> tuple[str, str, list[str]]:
    """Return (module, action, rest_args). Defaults to ('help', '', [])."""
    try:
        args = shlex.split((text or "").strip())
    except ValueError:
        args = text.split()
    if not args:
        return "help", "", []
    module = args[0].lower()
    action = args[1].lower() if len(args) > 1 else ""
    rest = args[2:]
    return module, action, rest


def _flag(rest: list[str], flag: str) -> str | None:
    try:
        idx = rest.index(flag)
        return rest[idx + 1] if idx + 1 < len(rest) else None
    except ValueError:
        return None


# ── Overflow helper ───────────────────────────────────────────────────────────

def _post_or_upload(
    client: Any,
    channel: str,
    user: str,
    blocks: list[dict],
    items: list[dict],
    filename: str,
    reply: Any = None,
) -> None:
    """Post blocks if they fit; otherwise upload as CSV."""
    if len(render_text(blocks)) <= 3000:
        if reply:
            reply(text="Result", blocks=blocks)
        else:
            client.chat_postEphemeral(channel=channel, user=user, blocks=blocks, text="Result")
    else:
        csv_bytes = overflow_to_csv(items)
        client.files_upload_v2(
            channel=channel,
            content=csv_bytes.decode(),
            filename=filename,
            title=filename,
            initial_comment="Result too long — attached as CSV.",
        )


# ── Access control ────────────────────────────────────────────────────────────
import os as _os


def _access_config() -> tuple[set[str], set[str]]:
    """Return (allowed_channels, allowed_users). Both must be set for the gate to activate."""
    raw_ch = _os.environ.get("ALLOWED_CHANNEL_IDS", "").strip()
    raw_usr = _os.environ.get("ALLOWED_USER_IDS", "").strip()
    channels = {c.strip() for c in raw_ch.split(",") if c.strip()}
    users = {u.strip() for u in raw_usr.split(",") if u.strip()}
    return channels, users


def _check_access(channel: str, user: str) -> str | None:
    """
    Combined Option-C gate.

    Rules:
    - If BOTH ALLOWED_CHANNEL_IDS and ALLOWED_USER_IDS are set:
        user must be in the user list AND channel must be in the channel list.
    - If only one is set: gate is inactive (warns at startup).
    - If neither is set: fully open.

    Returns an error string if access is denied, None if access is allowed.
    """
    allowed_ch, allowed_users = _access_config()
    gate_active = bool(allowed_ch) and bool(allowed_users)

    if not gate_active:
        return None  # unrestricted

    channel_ok = channel in allowed_ch
    user_ok = user in allowed_users

    if channel_ok and user_ok:
        return None  # both conditions met

    if not channel_ok:
        return ":no_entry: This bot is not enabled in this channel."
    return ":no_entry: You don't have permission to use this bot."


def _warn_partial_config() -> None:
    """Warn at startup if only one of the two env vars is set."""
    allowed_ch, allowed_users = _access_config()
    if bool(allowed_ch) != bool(allowed_users):
        import warnings
        missing = "ALLOWED_USER_IDS" if allowed_ch else "ALLOWED_CHANNEL_IDS"
        warnings.warn(
            f"[kolay-slack] Access control partially configured — {missing} is not set. "
            "The gate is INACTIVE. Set both vars to enable it.",
            stacklevel=2,
        )


# ── Main dispatcher ───────────────────────────────────────────────────────────

def dispatch(
    text: str,
    body: Any,
    client: Any,
    ack: Any,
    respond: Any = None,
) -> None:
    """Route a /kolay command to the appropriate handler."""
    ack()
    channel = body.get("channel_id") or ""
    user = body.get("user_id") or ""
    trigger_id = body.get("trigger_id") or ""

    # Use respond (response_url) if available — works without channel membership.
    # Fall back to chat_postEphemeral.
    def _reply(text: str = "", blocks: list | None = None, **extra: Any) -> None:
        kwargs: dict[str, Any] = {"text": text}
        if blocks:
            kwargs["blocks"] = blocks
        if respond:
            kwargs["response_type"] = "ephemeral"
            respond(**kwargs)
        else:
            kwargs["channel"] = channel
            kwargs["user"] = user
            client.chat_postEphemeral(**kwargs)

    # ── Combined Option-C gate ────────────────────────────────────────────────
    denial = _check_access(channel, user)
    if denial:
        _reply(text=denial)
        return

    module, action, rest = _parse(text)

    import os, threading
    env_tok = os.environ.get("KOLAY_API_TOKEN", "")
    print(f"[dispatch] module={module} action={action} KOLAY_API_TOKEN_len={len(env_tok)} thread={threading.current_thread().name}", flush=True)

    try:
        _route(module, action, rest, channel, user, trigger_id, client, _reply)
    except Exception as exc:  # noqa: BLE001
        _reply(text=f"Error: {exc}", blocks=error_block(str(exc)))




def _route(
    module: str,
    action: str,
    rest: list[str],
    channel: str,
    user: str,
    trigger_id: str,
    client: Any,
    reply: Any = None,
) -> None:
    # ── help ─────────────────────────────────────────────────────────────────
    if module in ("help", ""):
        if reply:
            reply(text="Kolay Help", blocks=_HELP_BLOCKS)
        else:
            client.chat_postEphemeral(
                channel=channel, user=user, blocks=_HELP_BLOCKS, text="Kolay Help"
            )
        return

    # ── settings ──────────────────────────────────────────────────────────────
    if module == "settings":
        _handle_settings(channel, user, trigger_id, client, body)
        return

    # ── quiz ─────────────────────────────────────────────────────────────────
    if module == "quiz":
        from .quiz import handle_quiz_command
        handle_quiz_command(
            ack=lambda: None,
            body={"user_id": user, "channel_id": channel},
            client=client,
            respond=reply,
        )
        return

    # ── person ────────────────────────────────────────────────────────────────
    if module == "person":
        if action in ("list", ""):
            search = _flag(rest, "--search") or (rest[0] if rest else None)
            result = person_svc.list_people(search=search, limit=20)
            items = result.get("items", [])
            keys = ["firstName", "lastName", "title", "department", "workEmail"]
            blocks = list_to_blocks(items, keys, f"👥 Employees ({len(items)})")
            _post_or_upload(client, channel, user, blocks, items, "employees.csv", reply)
        elif action == "view":
            pid = rest[0] if rest else None
            if not pid:
                if reply: reply(text=":x: Usage: `/kolaycli person view NAME_OR_ID`")
                else: client.chat_postEphemeral(channel=channel, user=user, text=":x: Usage: `/kolaycli person view NAME_OR_ID`")
                return
            p = person_svc.view_person(pid)
            keys = ["firstName", "lastName", "title", "department", "workEmail",
                    "gender", "employmentStartDate", "contractType", "status"]
            blocks = dict_to_fields(p, keys)
            if reply: reply(text=f"{p.get('firstName','')} {p.get('lastName','')}", blocks=blocks)
            else: client.chat_postEphemeral(channel=channel, user=user, blocks=blocks, text=f"{p.get('firstName','')} {p.get('lastName','')}")
        elif action in ("leave-status", "leave_status"):
            pid = rest[0] if rest else None
            if not pid:
                if reply: reply(text=":x: Usage: `/kolaycli person leave-status ID`")
                else: client.chat_postEphemeral(channel=channel, user=user, text=":x: Usage: `/kolaycli person leave-status ID`")
                return
            items = person_svc.leave_status(pid)
            keys = ["leaveTypeName", "usedDays", "remainingDays", "totalDays"]
            blocks = list_to_blocks(items, keys, "🏖️ Leave Balances")
            if reply: reply(text="Leave status", blocks=blocks)
            else: client.chat_postEphemeral(channel=channel, user=user, blocks=blocks, text="Leave status")
        else:
            if reply: reply(text=f":x: Unknown action `person {action}`. Try `/kolaycli help`.")
            else: client.chat_postEphemeral(channel=channel, user=user, text=f":x: Unknown action `person {action}`. Try `/kolaycli help`.")
        return

    # ── leave ─────────────────────────────────────────────────────────────────
    if module == "leave":
        if action in ("list", ""):
            items = leave_svc.list_leaves(limit=20)
            if not isinstance(items, list):
                items = []
            keys = ["person", "leaveType", "startDate", "endDate", "status"]
            blocks = list_to_blocks(items, keys, f"🏖️ Leaves ({len(items)})")
            _post_or_upload(client, channel, user, blocks, items, "leaves.csv", reply)
        elif action == "view":
            lid = rest[0] if rest else None
            if not lid:
                if reply: reply(text=":x: Usage: `/kolaycli leave view ID`")
                else: client.chat_postEphemeral(channel=channel, user=user, text=":x: Usage: `/kolaycli leave view ID`")
                return
            lv = leave_svc.view_leave(lid)
            blocks = dict_to_fields(lv)
            if reply: reply(text="Leave", blocks=blocks)
            else: client.chat_postEphemeral(channel=channel, user=user, blocks=blocks, text="Leave")
        elif action in ("request", "create"):
            view = build_leave_request_modal(trigger_id)
            client.views_open(trigger_id=trigger_id, view=view)
        else:
            if reply: reply(text=f":x: Unknown action `leave {action}`.")
            else: client.chat_postEphemeral(channel=channel, user=user, text=f":x: Unknown action `leave {action}`.")
        return

    # ── timelog ───────────────────────────────────────────────────────────────
    if module == "timelog":
        if action in ("list", ""):
            result = timelog_svc.list_timelogs(limit=20)
            items = result.get("items", [])
            keys = ["person", "type", "startDate", "endDate", "status"]
            blocks = list_to_blocks(items, keys, f"⏱️ Time Logs ({len(items)})")
            _post_or_upload(client, channel, user, blocks, items, "timelogs.csv", reply)
        elif action in ("create", "log"):
            view = build_timelog_create_modal()
            client.views_open(trigger_id=trigger_id, view=view)
        else:
            if reply: reply(text=f":x: Unknown action `timelog {action}`.")
            else: client.chat_postEphemeral(channel=channel, user=user, text=f":x: Unknown action `timelog {action}`.")
        return

    # ── unit ──────────────────────────────────────────────────────────────────
    if module == "unit":
        tree = unit_svc.unit_tree()
        lines = []
        def _walk(nodes: list, depth: int = 0) -> None:
            for n in nodes:
                lines.append("  " * depth + "• " + n.get("name", "?"))
                for item in n.get("items", []):
                    lines.append("  " * (depth + 1) + "- " + item.get("name", "?"))
                _walk(n.get("children", n.get("subUnits", [])), depth + 1)
        _walk(tree)
        text = "\n".join(lines) or "No org tree data."
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "🏢 Org Chart", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": text[:2900]}},
        ]
        if reply: reply(text="Org Chart", blocks=blocks)
        else: client.chat_postEphemeral(channel=channel, user=user, blocks=blocks, text="Org Chart")
        return

    # ── approval ──────────────────────────────────────────────────────────────
    if module == "approval":
        items = approval_svc.list_approval_processes()
        keys = ["name", "description", "status"]
        blocks = list_to_blocks(items, keys, f"✅ Approval Processes ({len(items)})")
        _post_or_upload(client, channel, user, blocks, items, "approvals.csv", reply)
        return

    # ── unknown ───────────────────────────────────────────────────────────────
    if reply:
        reply(text=f":x: Unknown module `{module}`. Try `/kolaycli help`.")
    else:
        client.chat_postEphemeral(
            channel=channel, user=user,
            text=f":x: Unknown module `{module}`. Try `/kolaycli help`."
        )


# ── Modal submission handlers ─────────────────────────────────────────────────

def handle_leave_request_submission(ack: Any, body: Any, client: Any) -> None:
    ack()
    vals = extract_leave_request_values(body)
    user_id = body["user"]["id"]
    channel = body.get("channel_id") or user_id  # DM fallback

    try:
        from ..services.person import resolve_person_id
        person_id = resolve_person_id(user_id)  # use Slack user_id lookup? fallback below
    except Exception:
        person_id = user_id  # will fail at API level with a clear message

    try:
        # leave_type is a name string from our static list — resolve to ID or pass as-is
        leave_svc.create_leave(
            person_id=person_id,
            leave_type_id=vals["leave_type"],
            start_date=vals["start_date"],
            end_date=vals["end_date"],
            comment=vals["comment"],
        )
        client.chat_postMessage(
            channel=user_id,
            text=f":white_check_mark: Leave requested from *{vals['start_date']}* to *{vals['end_date']}*.",
        )
    except Exception as exc:
        client.chat_postMessage(channel=user_id, text=f":x: Could not create leave: {exc}")


def handle_timelog_create_submission(ack: Any, body: Any, client: Any) -> None:
    ack()
    vals = extract_timelog_create_values(body)
    user_id = body["user"]["id"]

    try:
        from ..services.person import resolve_person_id
        person_id = resolve_person_id(vals["person"])
        timelog_svc.create_timelog(
            person_id=person_id,
            start=vals["start_date"] + " 09:00:00",
            end=vals["end_date"] + " 18:00:00",
            type=vals["type"],
            description=vals["description"],
        )
        client.chat_postMessage(
            channel=user_id,
            text=f":white_check_mark: Time log created for *{vals['person']}*.",
        )
    except Exception as exc:
        client.chat_postMessage(channel=user_id, text=f":x: Could not create timelog: {exc}")


# ── Settings command ──────────────────────────────────────────────────────────

def _handle_settings(
    channel: str,
    user: str,
    trigger_id: str,
    client: Any,
    body: Any,
) -> None:
    """Open the settings modal pre-filled with the current tenant config."""
    team_id = body.get("team_id") or (body.get("team") or {}).get("id", "")

    current_channels = ""
    current_users = ""
    try:
        from .tenant_store import TenantStore
        store = TenantStore()
        tenant = store.find(team_id)
        if tenant:
            current_channels = tenant.allowed_channels
            current_users = tenant.allowed_users
    except Exception:
        pass

    modal = build_settings_modal(
        current_channels=current_channels,
        current_users=current_users,
        team_id=team_id,
    )
    client.views_open(trigger_id=trigger_id, view=modal)


def handle_settings_submission(ack: Any, body: Any, client: Any) -> None:
    """Save updated settings from the modal to TenantStore."""
    ack()
    vals = extract_settings_values(body)
    user_id = body["user"]["id"]
    team_id = vals.get("team_id", "")

    if not team_id:
        client.chat_postMessage(channel=user_id, text=":x: Could not determine workspace.")
        return

    try:
        from .tenant_store import TenantStore
        store = TenantStore()
        tenant = store.find(team_id)

        if not tenant:
            client.chat_postMessage(
                channel=user_id,
                text=":x: This workspace is not registered. Please re-install the app.",
            )
            return

        if vals["allowed_channels"] or vals["allowed_channels"] == "":
            tenant.allowed_channels = vals["allowed_channels"]
        if vals["allowed_users"] or vals["allowed_users"] == "":
            tenant.allowed_users = vals["allowed_users"]
        if vals["kolay_api_token"]:
            tenant.kolay_api_token = vals["kolay_api_token"]

        store.upsert(tenant)

        parts = [":white_check_mark: *Settings updated!*"]
        if tenant.allowed_channels and tenant.allowed_users:
            parts.append(
                f"Access gate: *active* ({len(tenant.allowed_channels.split(','))} channel(s), "
                f"{len(tenant.allowed_users.split(','))} user(s))"
            )
        else:
            parts.append("Access gate: *inactive* (open to everyone)")
        if vals["kolay_api_token"]:
            parts.append("Kolay API token: *updated*")

        client.chat_postMessage(channel=user_id, text="\n".join(parts))

    except Exception as exc:
        client.chat_postMessage(channel=user_id, text=f":x: Could not save settings: {exc}")
