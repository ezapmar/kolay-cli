"""tests/test_turkish_holidays.py — Tests for the Turkish holiday calendar module."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

from kolay_cli.services.turkish_holidays import (
    get_holidays,
    is_off_day,
    is_weekend,
    _build_static,
)


class TestFixedHolidays:
    def test_new_years_day(self):
        result = _build_static(2026)
        assert date(2026, 1, 1) in result

    def test_republic_day(self):
        result = _build_static(2026)
        assert date(2026, 10, 29) in result
        assert date(2026, 10, 28) in result  # half-day arife

    def test_all_fixed_holidays_present_for_2025(self):
        result = _build_static(2025)
        fixed = [
            date(2025, 1, 1),   # Yilbasi
            date(2025, 4, 23),  # Cocuk Bayrami
            date(2025, 5, 1),   # Emek Gunu
            date(2025, 5, 19),  # Genclik Bayrami
            date(2025, 7, 15),  # Demokrasi Gunu
            date(2025, 8, 30),  # Zafer Bayrami
            date(2025, 10, 29), # Cumhuriyet
        ]
        for d in fixed:
            assert d in result, f"{d} missing from 2025 fixed holidays"

    def test_religious_holidays_2025(self):
        result = _build_static(2025)
        # Ramazan Bayrami
        assert date(2025, 3, 30) in result
        assert date(2025, 3, 31) in result
        assert date(2025, 4, 1)  in result
        # Kurban Bayrami
        assert date(2025, 6, 6)  in result
        assert date(2025, 6, 9)  in result

    def test_religious_holidays_2026(self):
        result = _build_static(2026)
        assert date(2026, 3, 20) in result  # Ramazan 1
        assert date(2026, 5, 27) in result  # Kurban 1

    def test_unknown_year_returns_only_fixed(self):
        # Year 2030 has no religious data — should still return fixed holidays
        result = _build_static(2030)
        assert date(2030, 1, 1) in result
        assert date(2030, 10, 29) in result
        # Should NOT have any religious holiday data (no key in _RELIGIOUS)
        assert len(result) == 8  # 8 fixed entries


class TestGetHolidays:
    def test_range_filters_correctly(self):
        holidays = get_holidays(date(2026, 5, 1), date(2026, 5, 31), try_gcal=False)
        assert date(2026, 5, 1) in holidays    # Emek Gunu
        assert date(2026, 5, 19) in holidays   # Genclik Bayrami
        assert date(2026, 5, 27) in holidays   # Kurban 1
        assert date(2026, 4, 23) not in holidays  # outside window

    def test_empty_range(self):
        holidays = get_holidays(date(2026, 9, 1), date(2026, 9, 10), try_gcal=False)
        # No holidays in first 10 days of September
        assert holidays == {}

    def test_staleness_warning_logged(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="kolay_cli.services.turkish_holidays"):
            get_holidays(date(2030, 1, 1), date(2030, 1, 10), try_gcal=False)
        assert any("2030" in r.message for r in caplog.records)

    def test_gcal_overlay_disabled(self):
        """With try_gcal=False, no network call should be attempted."""
        with patch("kolay_cli.services.turkish_holidays.urllib.request.urlopen") as mock_open:
            get_holidays(date(2026, 5, 1), date(2026, 5, 5), try_gcal=False)
        mock_open.assert_not_called()

    def test_gcal_failure_falls_back_silently(self):
        """If the Google Calendar fetch fails, static data is still returned."""
        with patch(
            "kolay_cli.services.turkish_holidays.urllib.request.urlopen",
            side_effect=OSError("network unavailable"),
        ):
            holidays = get_holidays(date(2026, 5, 1), date(2026, 5, 5), try_gcal=True)
        # Static data should still be returned despite network failure
        assert date(2026, 5, 1) in holidays


class TestIsOffDay:
    def test_saturday_is_off(self):
        sat = date(2026, 3, 21)  # Saturday
        assert is_weekend(sat) is True
        assert is_off_day(sat, {}) is True

    def test_sunday_is_off(self):
        sun = date(2026, 3, 22)  # Sunday
        assert is_weekend(sun) is True
        assert is_off_day(sun, {}) is True

    def test_monday_not_off_without_holiday(self):
        mon = date(2026, 3, 23)  # Monday
        assert is_weekend(mon) is False
        assert is_off_day(mon, {}) is False

    def test_holiday_makes_weekday_off(self):
        holidays = {date(2026, 5, 19): "Genclik Bayrami"}
        assert is_off_day(date(2026, 5, 19), holidays) is True
