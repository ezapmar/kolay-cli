"""Block Kit formatters — dict/list → Slack blocks, with CSV overflow."""
from __future__ import annotations

import csv
import io
from typing import Any


# ── helpers ──────────────────────────────────────────────────────────────────

def _str(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, dict):
        return v.get("name") or v.get("label") or str(v)
    if isinstance(v, list):
        return ", ".join(_str(i) for i in v) or "—"
    return str(v)


def _title_block(text: str) -> dict:
    return {
        "type": "header",
        "text": {"type": "plain_text", "text": text[:150], "emoji": True},
    }


def _divider() -> dict:
    return {"type": "divider"}


# ── public API ────────────────────────────────────────────────────────────────

def dict_to_fields(d: dict[str, Any], keys: list[str] | None = None) -> list[dict]:
    """Convert a dict to a Section block with mrkdwn fields (key/value pairs)."""
    items = [(k, d[k]) for k in (keys or d.keys()) if k in d]
    # Slack fields max 10 items per section; split into groups
    blocks = []
    chunk: list[dict] = []
    for k, v in items:
        label = k.replace("_", " ").title()
        chunk.append({"type": "mrkdwn", "text": f"*{label}:*\n{_str(v)}"})
        if len(chunk) == 10:
            blocks.append({"type": "section", "fields": chunk})
            chunk = []
    if chunk:
        blocks.append({"type": "section", "fields": chunk})
    return blocks


def list_to_blocks(
    items: list[dict[str, Any]],
    keys: list[str],
    title: str,
) -> list[dict]:
    """Convert a list of dicts to a Block Kit message (header + one section per item)."""
    blocks: list[dict] = [_title_block(title), _divider()]
    for item in items[:50]:
        fields = [
            {"type": "mrkdwn", "text": f"*{k.replace('_',' ').title()}:*\n{_str(item.get(k))}"}
            for k in keys
            if k in item
        ]
        if fields:
            blocks.append({"type": "section", "fields": fields[:10]})
            blocks.append(_divider())
    return blocks


def error_block(msg: str) -> list[dict]:
    return [{"type": "section", "text": {"type": "mrkdwn", "text": f":x: *Error:* {msg}"}}]


def success_block(msg: str) -> list[dict]:
    return [{"type": "section", "text": {"type": "mrkdwn", "text": f":white_check_mark: {msg}"}}]


def render_text(blocks: list[dict]) -> str:
    """Rough text estimate for length checks."""
    parts = []
    for b in blocks:
        if b.get("type") == "section":
            t = b.get("text", {})
            if t:
                parts.append(t.get("text", ""))
            for f in b.get("fields", []):
                parts.append(f.get("text", ""))
        elif b.get("type") == "header":
            parts.append(b.get("text", {}).get("text", ""))
    return "\n".join(parts)


def overflow_to_csv(items: list[dict[str, Any]]) -> bytes:
    """Serialize a list of dicts to UTF-8 CSV bytes."""
    if not items:
        return b""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(items[0].keys()), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(items)
    return buf.getvalue().encode()
