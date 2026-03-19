"""Behavioral Nudge Engine services."""
from __future__ import annotations

import time
from datetime import date
from typing import Any

from .. import config
from . import leave, timelog

def load_preferences() -> dict[str, Any]:
    raw = config.get_config_value("nudge", {})
    if not isinstance(raw, dict):
        raw = {}
    return {
        "style": raw.get("style", "gentle"),  # gentle, gamification, direct
        "cadence": raw.get("cadence", "daily"),
        "sprint_duration": int(raw.get("sprint_duration", 5)),
        "streak_count": int(raw.get("streak_count", 0)),
        "last_all_clear_date": raw.get("last_all_clear_date", ""),
        "last_nudge_time": float(raw.get("last_nudge_time", 0.0)),
        "nudge_count_today": int(raw.get("nudge_count_today", 0)),
        "last_nudge_date": raw.get("last_nudge_date", ""),
    }

def save_preferences(prefs: dict[str, Any]) -> None:
    current = config.get_config_value("nudge", {})
    if not isinstance(current, dict):
        current = {}
    current.update(prefs)
    config.set_config_value("nudge", current)

def should_throttle_bare_command() -> bool:
    """Check if we should suppress a nudge on the bare command based on traffic control."""
    prefs = load_preferences()
    today = date.today().isoformat()
    if prefs["last_nudge_date"] != today:
        return False  # new day, never throttle first one
    
    # Allow max 3 bare command nudges per day
    if prefs["nudge_count_today"] >= 3:
        return True
        
    # Minimum 2 hours (7200s) between bare nudges
    now = time.time()
    if (now - prefs["last_nudge_time"]) < 7200:
        return True
        
    return False

def record_bare_nudge_shown() -> None:
    prefs = load_preferences()
    today = date.today().isoformat()
    if prefs["last_nudge_date"] != today:
        prefs["last_nudge_date"] = today
        prefs["nudge_count_today"] = 0
    
    prefs["nudge_count_today"] += 1
    prefs["last_nudge_time"] = time.time()
    save_preferences(prefs)

def update_streak() -> int:
    """Called when an 'all clear' state is detected."""
    prefs = load_preferences()
    today = date.today()
    last = prefs["last_all_clear_date"]
    streak = prefs["streak_count"]
    
    if last == today.isoformat():
        return streak  # already counted today
        
    if last:
        last_date = date.fromisoformat(last)
        if (today - last_date).days == 1:
            streak += 1
        else:
            streak = 1  # broken streak
    else:
        streak = 1
        
    prefs["last_all_clear_date"] = today.isoformat()
    prefs["streak_count"] = streak
    save_preferences(prefs)
    return streak

def analyze_pending_work() -> list[dict[str, Any]]:
    """Gather pending items across services."""
    pending = []
    
    try:
        # Check waiting leaves
        res_leaves = leave.list_leaves(status="waiting", limit=15)
        for lv in res_leaves:
            person_name = ""
            if "person" in lv:
                person_name = f"{lv['person'].get('firstName', '')} {lv['person'].get('lastName', '')}".strip()
            
            pending.append({
                "type": "leave",
                "id": lv.get("id"),
                "title": f"Leave Request from {person_name or 'Employee'}",
                "detail": "Requires approval",
                "raw": lv
            })
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("Failed reading waiting leaves for nudge: %s", exc)
        
    try:
        # Check waiting timelogs
        res_tl = timelog.list_timelogs(status="waiting", limit=15)
        for tl in res_tl.get("items", []):
            person_name = ""
            if "person" in tl:
                person_name = f"{tl['person'].get('firstName', '')} {tl['person'].get('lastName', '')}".strip()
            
            desc = tl.get("description", "Timelog entry")
            pending.append({
                "type": "timelog",
                "id": tl.get("id"),
                "title": f"Timelog from {person_name or 'Employee'}",
                "detail": desc,
                "raw": tl
            })
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("Failed reading waiting timelogs for nudge: %s", exc)

    return pending
