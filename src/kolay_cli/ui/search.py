"""
Client-side search/filtering utilities for kolay-cli.

All list commands can pipe their API results through ``filter_items`` to give
the user an instant, offline ``--filter`` / ``-f`` flag.  No API changes needed.
"""
from __future__ import annotations
from typing import Any, Callable

from .formatters import console
from .constants import PRIMARY


def filter_items(
    items: list[dict[str, Any]],
    query: str | None,
    key_fns: list[Callable[[dict[str, Any]], str]],
    *,
    label: str = "records",
) -> list[dict[str, Any]]:
    """Case-insensitive substring filter across multiple fields.

    Args:
        items:   Full list of dicts returned by the API.
        query:   The user's search term (``--filter`` value). If ``None`` or
                 empty, the original list is returned unchanged.
        key_fns: Callables that extract a single searchable string from each
                 item (e.g. ``lambda p: p.get("firstName", "")``).
                 A match on *any* key wins.
        label:   Human-readable noun used in the count message (e.g. ``"employees"``).

    Returns:
        Filtered list (may be empty). Prints a summary when filtering is active.
    """
    if not query or not query.strip():
        return items

    q = query.strip().lower()
    matched = [
        item for item in items
        if any(q in fn(item).lower() for fn in key_fns)
    ]

    total = len(items)
    found = len(matched)
    if found == total:
        # All records matched — don't clutter output
        return matched

    if found:
        console.print(
            f" [grey62]Showing {found} of {total} {label} matching "
            f"[bold]{query}[/bold][grey62].[/grey62]\n"
        )
    else:
        console.print(
            f" [grey62]No {label} matched [bold]{query}[/bold][grey62]. "
            f"Showing all {total}.[/grey62]\n"
        )
        return items  # fallback — show everything rather than a blank screen

    return matched


def filter_items_silent(
    items: list[dict[str, Any]],
    query: str | None,
    key_fns: list[Callable[[dict[str, Any]], str]],
) -> list[dict[str, Any]]:
    """Same as ``filter_items`` but without Rich console output.

    Designed for the MCP server where printing would corrupt the JSON
    transport stream.  Returns the full list when *query* is empty or
    ``None``.
    """
    if not query or not query.strip():
        return items

    q = query.strip().lower()
    matched = [
        item for item in items
        if any(q in fn(item).lower() for fn in key_fns)
    ]
    return matched if matched else items
