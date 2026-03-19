"""Turkish public holiday calendar.

Fixed national holidays + pre-computed religious holidays via Google Calendar
iCal feed (tr.turkish#holiday@group.v.calendar.google.com).

The static dict covers 2024-2027. A staleness warning is logged when the
current year extends beyond the known data.
"""
from __future__ import annotations

import logging
import urllib.request
from datetime import date, timedelta
from typing import Any

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static fallback: fixed national holidays (MM-DD)
# ---------------------------------------------------------------------------
_FIXED: list[tuple[str, str]] = [
    ("01-01", "Yilbasi (Yeni Yil)"),
    ("04-23", "Ulusal Egemenlik ve Cocuk Bayrami"),
    ("05-01", "Emek ve Dayanisma Gunu"),
    ("05-19", "Ataturk'u Anma, Genclik ve Spor Bayrami"),
    ("07-15", "Demokrasi ve Milli Birlik Gunu"),
    ("08-30", "Zafer Bayrami"),
    ("10-28", "Cumhuriyet Bayrami arifesi (14:00'dan itibaren)"),
    ("10-29", "Cumhuriyet Bayrami"),
]

# ---------------------------------------------------------------------------
# Static religious holidays — pre-computed for 2024-2027
# (Lunar calendar — these shift ~11 days earlier each year)
# Source: official Turkish government announcements + timeanddate.com
# ---------------------------------------------------------------------------
_RELIGIOUS: dict[str, list[tuple[date, str]]] = {
    "2024": [
        (date(2024, 4, 10), "Ramazan Bayrami 1. Gunu"),
        (date(2024, 4, 11), "Ramazan Bayrami 2. Gunu"),
        (date(2024, 4, 12), "Ramazan Bayrami 3. Gunu"),
        (date(2024, 6, 17), "Kurban Bayrami Arifesi"),
        (date(2024, 6, 18), "Kurban Bayrami 1. Gunu"),
        (date(2024, 6, 19), "Kurban Bayrami 2. Gunu"),
        (date(2024, 6, 20), "Kurban Bayrami 3. Gunu"),
        (date(2024, 6, 21), "Kurban Bayrami 4. Gunu"),
    ],
    "2025": [
        (date(2025, 3, 29), "Ramazan Bayrami Arifesi"),
        (date(2025, 3, 30), "Ramazan Bayrami 1. Gunu"),
        (date(2025, 3, 31), "Ramazan Bayrami 2. Gunu"),
        (date(2025, 4, 1),  "Ramazan Bayrami 3. Gunu"),
        (date(2025, 6, 5),  "Kurban Bayrami Arifesi"),
        (date(2025, 6, 6),  "Kurban Bayrami 1. Gunu"),
        (date(2025, 6, 7),  "Kurban Bayrami 2. Gunu"),
        (date(2025, 6, 8),  "Kurban Bayrami 3. Gunu"),
        (date(2025, 6, 9),  "Kurban Bayrami 4. Gunu"),
    ],
    "2026": [
        (date(2026, 3, 19), "Ramazan Bayrami Arifesi"),
        (date(2026, 3, 20), "Ramazan Bayrami 1. Gunu"),
        (date(2026, 3, 21), "Ramazan Bayrami 2. Gunu"),
        (date(2026, 3, 22), "Ramazan Bayrami 3. Gunu"),
        (date(2026, 5, 26), "Kurban Bayrami Arifesi"),
        (date(2026, 5, 27), "Kurban Bayrami 1. Gunu"),
        (date(2026, 5, 28), "Kurban Bayrami 2. Gunu"),
        (date(2026, 5, 29), "Kurban Bayrami 3. Gunu"),
        (date(2026, 5, 30), "Kurban Bayrami 4. Gunu"),
    ],
    "2027": [
        (date(2027, 3, 9),  "Ramazan Bayrami Arifesi"),
        (date(2027, 3, 10), "Ramazan Bayrami 1. Gunu"),
        (date(2027, 3, 11), "Ramazan Bayrami 2. Gunu"),
        (date(2027, 3, 12), "Ramazan Bayrami 3. Gunu"),
        (date(2027, 5, 16), "Kurban Bayrami Arifesi"),
        (date(2027, 5, 17), "Kurban Bayrami 1. Gunu"),
        (date(2027, 5, 18), "Kurban Bayrami 2. Gunu"),
        (date(2027, 5, 19), "Kurban Bayrami 3. Gunu"),
        (date(2027, 5, 20), "Kurban Bayrami 4. Gunu"),
    ],
}

# Google Calendar iCal feed for Turkish public holidays
_GCAL_ICAL_URL = (
    "https://calendar.google.com/calendar/ical/"
    "tr.turkish%23holiday%40group.v.calendar.google.com/public/basic.ics"
)

# Cached result from optional remote fetch
_gcal_cache: dict[date, str] | None = None


def _build_static(year: int) -> dict[date, str]:
    """Build a date → name map for `year` using static data only."""
    result: dict[date, str] = {}
    for mmdd, name in _FIXED:
        try:
            result[date(year, int(mmdd[:2]), int(mmdd[3:]))] = name
        except ValueError:
            pass  # Feb-29 on non-leap year, etc.
    for entry_date, name in _RELIGIOUS.get(str(year), []):
        result[entry_date] = name
    return result


def _parse_ical(ical_text: str) -> dict[date, str]:
    """Minimal iCal VEVENT parser — only reads DTSTART and SUMMARY."""
    events: dict[date, str] = {}
    current: dict[str, str] = {}
    in_event = False
    for raw_line in ical_text.splitlines():
        line = raw_line.strip()
        if line == "BEGIN:VEVENT":
            in_event = True
            current = {}
        elif line == "END:VEVENT":
            if in_event and "DTSTART" in current and "SUMMARY" in current:
                try:
                    ds = current["DTSTART"].replace(";VALUE=DATE", "")[:8]
                    d = date(int(ds[:4]), int(ds[4:6]), int(ds[6:8]))
                    events[d] = current["SUMMARY"]
                except (ValueError, IndexError):
                    pass
            in_event = False
        elif in_event and ":" in line:
            key, _, value = line.partition(":")
            current[key] = value
    return events


def _fetch_gcal() -> dict[date, str] | None:
    """Try to fetch and parse Google Calendar iCal. Returns None on any error."""
    global _gcal_cache
    if _gcal_cache is not None:
        return _gcal_cache
    try:
        with urllib.request.urlopen(_GCAL_ICAL_URL, timeout=3) as resp:  # nosec B310
            text = resp.read().decode("utf-8", errors="ignore")
        _gcal_cache = _parse_ical(text)
        _log.debug("[wellness-engine] Google Calendar holidays fetched: %d entries", len(_gcal_cache))
        return _gcal_cache
    except Exception as exc:
        _log.debug("[wellness-engine] Google Calendar fetch failed (%s) — using static fallback", exc)
        return None


def get_holidays(
    start: date,
    end: date,
    *,
    try_gcal: bool = True,
) -> dict[date, str]:
    """Return {date: name} for all Turkish public holidays in [start, end].

    Tries the Google Calendar iCal feed first (Option B overlay), then falls
    back to the static pre-computed table (Option A backbone).
    A staleness warning is emitted when the year is beyond known static data.
    """
    years_needed = set(range(start.year, end.year + 1))
    max_known_year = max(int(y) for y in _RELIGIOUS)
    for yr in sorted(years_needed):
        if yr > max_known_year:
            _log.warning(
                "[wellness-engine] Turkish holiday data for %d is not available "
                "(latest known: %d). Update turkish_holidays.py.",
                yr, max_known_year,
            )

    # Attempt live fetch (Option B) — supplement/override static data
    gcal: dict[date, str] | None = _fetch_gcal() if try_gcal else None

    result: dict[date, str] = {}
    cursor = start
    while cursor <= end:
        # Option A: static
        static_map = _build_static(cursor.year)
        if cursor in static_map:
            result[cursor] = static_map[cursor]
        # Option B: gcal overlay (overwrites with richer name if available)
        if gcal and cursor in gcal:
            result[cursor] = gcal[cursor]
        cursor += timedelta(days=1)

    return result


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5  # Saturday=5, Sunday=6


def is_off_day(d: date, holidays: dict[date, str]) -> bool:
    return is_weekend(d) or d in holidays
