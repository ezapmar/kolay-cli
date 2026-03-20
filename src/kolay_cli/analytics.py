"""Local-first, opt-in usage analytics for kolay-cli.

All data stays on disk at ``~/.config/kolay/analytics.json``.
Nothing is ever sent over the network.

Enable:  ``kolay config set analytics_enabled true``
Disable: ``kolay config set analytics_enabled false``
View:    ``kolay analytics``
Reset:   ``kolay analytics --reset``
"""
from __future__ import annotations

import json
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


_ANALYTICS_FILE = Path.home() / ".config" / "kolay" / "analytics.json"


# ── Opt-in gate ───────────────────────────────────────────────────────────────

def is_enabled() -> bool:
    """Check if analytics is opted-in via config."""
    try:
        from .config import get_config_value
        val = get_config_value("analytics_enabled", False)
        return str(val).lower() in ("true", "1", "yes")
    except Exception:
        return False


# ── Storage ───────────────────────────────────────────────────────────────────

def _load() -> dict[str, Any]:
    try:
        if _ANALYTICS_FILE.exists():
            return json.loads(_ANALYTICS_FILE.read_text("utf-8"))
    except Exception:
        pass
    return {"events": [], "first_seen": date.today().isoformat()}


def _save(data: dict[str, Any]) -> None:
    try:
        _ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ANALYTICS_FILE.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
    except Exception:
        pass


# ── Recording ─────────────────────────────────────────────────────────────────

def record(command: str, *, duration_ms: float = 0, success: bool = True) -> None:
    """Append a single event. No-op if analytics is disabled."""
    if not is_enabled():
        return
    data = _load()
    # Cap at 5000 events (rolling window — drop oldest)
    events: list[dict[str, Any]] = data.get("events", [])
    events.append({
        "cmd": command,
        "day": date.today().isoformat(),
        "ms": round(duration_ms),
        "ok": success,
    })
    if len(events) > 5000:
        events = events[-5000:]
    data["events"] = events
    _save(data)


# ── Analysis ──────────────────────────────────────────────────────────────────

def summarize() -> dict[str, Any]:
    """Produce a human-readable analytics summary from local data."""
    data = _load()
    events = data.get("events", [])
    if not events:
        return {"total_commands": 0, "message": "No usage data yet."}

    cmds = Counter(e["cmd"] for e in events)
    days = Counter(e["day"] for e in events)
    errors = sum(1 for e in events if not e.get("ok", True))
    durations = [e.get("ms", 0) for e in events if e.get("ms")]

    # Active days
    active_days = len(days)
    first_day = data.get("first_seen", min(days.keys()))
    today = date.today()
    try:
        total_days = (today - date.fromisoformat(first_day)).days + 1
    except Exception:
        total_days = active_days

    # Streaks
    sorted_days = sorted(days.keys())
    current_streak = 0
    if sorted_days:
        streak = 1
        for i in range(len(sorted_days) - 1, 0, -1):
            d1 = date.fromisoformat(sorted_days[i])
            d2 = date.fromisoformat(sorted_days[i - 1])
            if (d1 - d2).days == 1:
                streak += 1
            else:
                break
        current_streak = streak

    # Busiest day of week
    weekday_counts: Counter[str] = Counter()
    for day_str in days:
        try:
            d = date.fromisoformat(day_str)
            weekday_counts[d.strftime("%A")] += days[day_str]
        except Exception:
            pass
    busiest_weekday = weekday_counts.most_common(1)[0][0] if weekday_counts else "N/A"

    # Peak hour (from event timestamps if available, otherwise skip)
    avg_ms = round(sum(durations) / len(durations)) if durations else 0

    return {
        "total_commands": len(events),
        "unique_commands": len(cmds),
        "top_commands": cmds.most_common(10),
        "active_days": active_days,
        "total_days_since_install": total_days,
        "current_streak": current_streak,
        "busiest_weekday": busiest_weekday,
        "error_count": errors,
        "error_rate_pct": round(errors / len(events) * 100, 1) if events else 0,
        "avg_duration_ms": avg_ms,
        "first_seen": first_day,
    }


def reset() -> None:
    """Wipe all local analytics data."""
    _save({"events": [], "first_seen": date.today().isoformat()})
