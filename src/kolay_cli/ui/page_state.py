"""
Cross-page row-number resolution state for kolay-cli.

After each ``list`` command renders its table, ``save_page_state()`` records
which resource type, page, and limit was shown.  ``_resolve_*_id`` functions
call ``load_page_state()`` to honour the user's last-seen page so that
``kolay person view 3`` after ``kolay person list --page 2`` correctly returns
item 3 *of page 2* (row offset 23), not item 3 of page 1.

The state file lives at ``~/.config/kolay/.page_state.json`` and is ignored
if older than PAGE_STATE_TTL_SECONDS (600 s = 10 minutes) to avoid stale
cross-session surprises.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_STATE_FILE = Path.home() / ".config" / "kolay" / ".page_state.json"
PAGE_STATE_TTL_SECONDS = 600  # 10 minutes


def save_page_state(
    *,
    resource: str,
    page: int,
    limit: int,
    total: int,
) -> None:
    """Persist the last-listed page context for a given resource.

    Args:
        resource: Short key identifying the command, e.g. ``"person"`` or
                  ``"timelog"``.  Must match what ``load_page_state`` checks.
        page:     1-based page number that was just rendered.
        limit:    Records per page.
        total:    Total server-side record count (used for bounds checking).
    """
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "resource": resource,
            "page": page,
            "limit": limit,
            "total": total,
            "ts": time.time(),
        }
        _STATE_FILE.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass  # non-fatal — degraded gracefully to page-1 resolution


def load_page_state(resource: str) -> dict[str, int] | None:
    """Return the saved page state for *resource* if it is recent enough.

    Returns ``None`` when:
    - The state file does not exist.
    - The state is for a *different* resource (e.g. user ran ``person list``
      but is now calling ``kolay timelog view``).
    - The state is older than ``PAGE_STATE_TTL_SECONDS``.

    Returns a dict with keys ``page``, ``limit``, ``total`` otherwise.
    """
    try:
        raw = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if raw.get("resource") != resource:
        return None

    age = time.time() - float(raw.get("ts", 0))
    if age > PAGE_STATE_TTL_SECONDS:
        return None

    return {
        "page": int(raw["page"]),
        "limit": int(raw["limit"]),
        "total": int(raw["total"]),
    }


def clear_page_state() -> None:
    """Remove the saved page state (called from unit tests)."""
    try:
        _STATE_FILE.unlink(missing_ok=True)
    except OSError:
        pass
