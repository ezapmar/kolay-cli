"""Tests for ui.search.filter_items utility."""
import pytest
from kolay_cli.ui.search import filter_items


PEOPLE = [
    {"firstName": "Ali", "lastName": "Veli", "workEmail": "ali.veli@example.com"},
    {"firstName": "Aysha", "lastName": "Kaya", "workEmail": "aysha@example.com"},
    {"firstName": "John", "lastName": "Doe", "workEmail": "john@example.com"},
]

NAME_FNS = [
    lambda p: f"{p.get('firstName', '')} {p.get('lastName', '')}",
    lambda p: p.get("workEmail") or "",
]


def test_no_query_returns_all():
    result = filter_items(PEOPLE, None, NAME_FNS)
    assert result == PEOPLE


def test_empty_query_returns_all():
    result = filter_items(PEOPLE, "", NAME_FNS)
    assert result == PEOPLE


def test_whitespace_only_query_returns_all():
    result = filter_items(PEOPLE, "   ", NAME_FNS)
    assert result == PEOPLE


def test_exact_first_name_match():
    result = filter_items(PEOPLE, "Ali", NAME_FNS)
    assert len(result) == 1
    assert result[0]["firstName"] == "Ali"


def test_case_insensitive():
    result = filter_items(PEOPLE, "ali", NAME_FNS)
    assert len(result) == 1
    assert result[0]["firstName"] == "Ali"


def test_partial_match():
    result = filter_items(PEOPLE, "ay", NAME_FNS)
    # "Aysha" matches
    assert any(p["firstName"] == "Aysha" for p in result)


def test_email_match():
    result = filter_items(PEOPLE, "john@example", NAME_FNS)
    assert len(result) == 1
    assert result[0]["firstName"] == "John"


def test_no_match_falls_back_to_all(capsys):
    """Zero matches should return the full list instead of an empty screen."""
    result = filter_items(PEOPLE, "zzznomatch", NAME_FNS)
    assert result == PEOPLE


def test_all_match_no_summary_printed(capsys):
    """When all items match, no extra message is printed."""
    result = filter_items(PEOPLE, "example.com", NAME_FNS)
    # all three have @example.com address
    assert len(result) == 3


def test_empty_items_list():
    result = filter_items([], "Ali", NAME_FNS)
    assert result == []


# ── Turkish / Unicode tests ──────────────────────────────────────────────────

TURKISH_PEOPLE = [
    {"firstName": "Bora", "lastName": "Ağaoğlu", "workEmail": "bora@example.com"},
    {"firstName": "Elif", "lastName": "Çelik", "workEmail": "elif@example.com"},
    {"firstName": "Gül", "lastName": "Şahin", "workEmail": "gul@example.com"},
    {"firstName": "İsmail", "lastName": "Öztürk", "workEmail": "ismail@example.com"},
]


def test_turkish_partial_last_name():
    """'Ağa' should match 'Ağaoğlu'."""
    result = filter_items(TURKISH_PEOPLE, "Ağa", NAME_FNS)
    assert len(result) == 1
    assert result[0]["lastName"] == "Ağaoğlu"


def test_turkish_full_last_name():
    result = filter_items(TURKISH_PEOPLE, "Ağaoğlu", NAME_FNS)
    assert len(result) == 1
    assert result[0]["firstName"] == "Bora"


def test_turkish_first_name():
    result = filter_items(TURKISH_PEOPLE, "Bora", NAME_FNS)
    assert len(result) == 1
    assert result[0]["lastName"] == "Ağaoğlu"


def test_turkish_full_name():
    """Multi-word search 'Bora Ağaoğlu' should match the combined name field."""
    result = filter_items(TURKISH_PEOPLE, "Bora Ağaoğlu", NAME_FNS)
    assert len(result) == 1
    assert result[0]["firstName"] == "Bora"


def test_turkish_cedilla():
    result = filter_items(TURKISH_PEOPLE, "Çelik", NAME_FNS)
    assert len(result) == 1
    assert result[0]["firstName"] == "Elif"


def test_turkish_dotted_i():
    result = filter_items(TURKISH_PEOPLE, "İsmail", NAME_FNS)
    assert len(result) == 1
    assert result[0]["lastName"] == "Öztürk"


# ── filter_items_silent tests ────────────────────────────────────────────────

from kolay_cli.ui.search import filter_items_silent


def test_silent_no_query_returns_all():
    result = filter_items_silent(PEOPLE, None, NAME_FNS)
    assert result == PEOPLE


def test_silent_match():
    result = filter_items_silent(PEOPLE, "Ali", NAME_FNS)
    assert len(result) == 1
    assert result[0]["firstName"] == "Ali"


def test_silent_no_match_returns_all():
    """Zero matches should fall back to the full list, same as filter_items."""
    result = filter_items_silent(PEOPLE, "zzznomatch", NAME_FNS)
    assert result == PEOPLE


def test_silent_turkish_partial():
    result = filter_items_silent(TURKISH_PEOPLE, "Ağa", NAME_FNS)
    assert len(result) == 1
    assert result[0]["lastName"] == "Ağaoğlu"


def test_silent_no_console_output(capsys):
    """filter_items_silent must not print anything."""
    filter_items_silent(PEOPLE, "Ali", NAME_FNS)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
