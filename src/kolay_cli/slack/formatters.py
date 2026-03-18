"""Block Kit formatters — dict/list → Slack blocks, with CSV overflow & pagination."""
from __future__ import annotations

import csv
import hashlib
import io
import json
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
    blocks: list[dict] = []
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


# ── Compact list view ────────────────────────────────────────────────────────

# Column display config per resource type
_COLUMN_CONFIG: dict[str, list[tuple[str, str, int]]] = {
    # (key, emoji_label, max_width)
    "person": [
        ("firstName", "👤", 12),
        ("lastName", "", 12),
        ("title", "💼", 20),
        ("department", "🏢", 15),
    ],
    "leave": [
        ("person", "👤", 20),
        ("leaveType", "📋", 15),
        ("startDate", "📅", 10),
        ("endDate", "→", 10),
        ("status", "🔵", 8),
    ],
    "timelog": [
        ("person", "👤", 20),
        ("type", "📋", 12),
        ("startDate", "📅", 10),
        ("endDate", "→", 10),
        ("status", "🔵", 8),
    ],
    "approval": [
        ("name", "📋", 25),
        ("description", "📝", 30),
        ("status", "🔵", 10),
    ],
}

ITEMS_PER_PAGE = 10  # How many items per page


def _format_row(item: dict, cols: list[tuple[str, str, int]], idx: int) -> str:
    """Format a single item as a compact row."""
    parts = []
    for key, emoji, max_w in cols:
        val = _str(item.get(key, ""))
        if len(val) > max_w:
            val = val[:max_w - 1] + "…"
        if emoji:
            parts.append(f"{emoji} {val}")
        else:
            parts.append(val)
    return f"`{idx:>2}.` " + " · ".join(parts)


def compact_list_blocks(
    items: list[dict[str, Any]],
    resource: str,
    title: str,
    page: int = 1,
    total_count: int | None = None,
    search: str | None = None,
) -> list[dict]:
    """Build a compact, paginated list view within Slack's block limits.

    Returns blocks for the current page with optional pagination buttons.
    """
    cols = _COLUMN_CONFIG.get(resource, [
        (k, "", 20) for k in (list(items[0].keys())[:4] if items else [])
    ])

    total = total_count or len(items)
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = items[start:end]

    blocks: list[dict] = [_title_block(title)]

    if not page_items:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_No results found._"},
        })
        return blocks

    # Build compact rows — group ~5 rows per section block to stay under limits
    rows: list[str] = []
    for i, item in enumerate(page_items, start=start + 1):
        rows.append(_format_row(item, cols, i))

    # Group rows into section blocks (5 rows per block for readability)
    ROWS_PER_BLOCK = 5
    for chunk_start in range(0, len(rows), ROWS_PER_BLOCK):
        chunk = rows[chunk_start:chunk_start + ROWS_PER_BLOCK]
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(chunk)},
        })

    # Footer with page info
    search_info = f"  •  🔍 `{search}`" if search else ""
    footer = f"_Page {page}/{total_pages}  •  {total} total{search_info}_"
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": footer}]})

    # Pagination buttons
    if total_pages > 1:
        buttons: list[dict] = []
        if page > 1:
            buttons.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "◀ Previous", "emoji": True},
                "action_id": f"page_{resource}_{page - 1}",
                "value": json.dumps({
                    "resource": resource,
                    "page": page - 1,
                    "search": search or "",
                }),
            })
        if page < total_pages:
            buttons.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "Next ▶", "emoji": True},
                "action_id": f"page_{resource}_{page + 1}",
                "value": json.dumps({
                    "resource": resource,
                    "page": page + 1,
                    "search": search or "",
                }),
            })
        if buttons:
            blocks.append({"type": "actions", "elements": buttons})

    return blocks


# ── Legacy list (kept for compatibility) ─────────────────────────────────────

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
