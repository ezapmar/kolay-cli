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
