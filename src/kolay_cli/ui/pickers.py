"""Interactive pickers for kolay-cli."""
from __future__ import annotations
import random
from typing import Any, Callable, TYPE_CHECKING
import typer as _typer
from rich.table import Table

from .constants import (
    PRIMARY,
    _PICKER_QUIPS, _LEAVE_PICKER_QUIPS, _TRX_PICKER_QUIPS, _EVENT_PICKER_QUIPS,
    _TIMELOG_PICKER_QUIPS, _TRAINING_PICKER_QUIPS, _PERSON_TRAINING_PICKER_QUIPS,
    _FILE_PICKER_QUIPS,
)
from .formatters import console, short_id, display_status, fmt_num, fmt_datetime

if TYPE_CHECKING:
    from ..api.client import KolayClient


def _base_pick(
    client: KolayClient | None,
    quips: list[str],
    prompt: str,
    fetch_fn: Callable[[KolayClient], list[dict[str, Any]]],
    table_factory: Callable[[list[dict[str, Any]]], Table],
    confirm_fn: Callable[[dict[str, Any]], str],
    search_keys: list[Callable[[dict[str, Any]], str]] | None = None,
    *,
    fetch_more_fn: Callable[[KolayClient, int], list[dict[str, Any]]] | None = None,
    limit_hint: int = 0,
) -> str:
    """Core logic for interactive pickers.

    Fetches data, optionally filters by search term, renders a table, and
    prompts for selection.

    Args:
        fetch_fn:      Callable that takes a client and returns the initial
                       item list.
        fetch_more_fn: Optional callable ``(client, new_limit) -> items`` for
                       the "Load more?" prompt.  When provided and
                       ``len(items) == limit_hint``, the picker offers to
                       double the batch size before the selection prompt.
        limit_hint:    The limit used in the initial fetch.  Used to detect
                       whether the list may be truncated.
    """
    from ..api.client import KolayClient
    from ..api.errors import APIError
    from .search import filter_items

    if client is None:
        try:
            client = KolayClient()
        except APIError as exc:
            print_error_inline(str(exc))
            return _prompt_or_abort(prompt)

    console.print(f"\n[grey62]{random.choice(quips)}[/grey62]\n")  # nosec B311 — cosmetic UI quip, not crypto

    try:
        with console.status(f"[{PRIMARY}]Fetching...[/{PRIMARY}]", spinner="dots"):
            items = fetch_fn(client)
    except APIError as exc:
        status = getattr(exc, "status_code", "Unknown")
        msg = str(exc.message if hasattr(exc, "message") else exc)
        console.print(f"[grey62]  [bold]Couldn't fetch the list ({status} — {msg}).[/bold] Enter ID manually or press Enter to abort.[/grey62]")
        return _prompt_or_abort(prompt)

    if not items:
        console.print(f"[grey62]  No {prompt.lower()} records found.[/grey62]")
        return _prompt_or_abort(prompt)

    if search_keys:
        query = _typer.prompt(
            f"  Filter {prompt.lower()}s (leave blank for all)",
            default="",
        )
        if query.strip():
            items = filter_items(items, query, search_keys, label=f"{prompt.lower()}s")

    # ── "Load more?" loop ────────────────────────────────────────────────────
    current_limit = limit_hint or len(items)
    while fetch_more_fn and len(items) >= current_limit:
        console.print(table_factory(items))
        console.print(
            f"\n  [grey50]Showing {len(items)} records — there may be more.[/grey50]"
            f"\n  [grey50]Load more?[/grey50] [bold](y/N)[/bold] ",
            end="",
        )
        answer = _typer.prompt("", default="n", show_default=False).strip().lower()
        if answer not in ("y", "yes"):
            break
        new_limit = current_limit * 2
        console.print(f"  [grey62]Fetching up to {new_limit}…[/grey62]")
        try:
            with console.status(f"[{PRIMARY}]Loading more...[/{PRIMARY}]", spinner="dots"):
                more = fetch_more_fn(client, new_limit)
            if more:
                items = more
                current_limit = new_limit
            else:
                console.print("  [grey62]No additional records found.[/grey62]")
                break
        except APIError as exc:
            console.print(f"  [grey62]Couldn't load more: {exc}[/grey62]")
            break

    console.print(table_factory(items))
    console.print()

    raw = _typer.prompt(f"  Pick a {prompt.lower()} (# or ID)")

    try:
        idx = int(raw.strip()) - 1
        if 0 <= idx < len(items):
            chosen = items[idx]
            console.print(f"  [{PRIMARY}]→ {confirm_fn(chosen)}[/{PRIMARY}]\n")
            return str(chosen.get("id", ""))
        # out of range — treat as raw ID
        return raw.strip()
    except ValueError:
        return raw.strip()


def print_error_inline(msg: str) -> None:
    """Lightweight inline error for use inside pickers."""
    from .constants import ERROR
    console.print(f"[{ERROR}]  ✘ {msg}[/{ERROR}]")


def _prompt_or_abort(prompt: str) -> str:
    """Prompt for a manual ID once. If the user leaves it blank, abort cleanly.

    This prevents infinite loops when a picker can't fetch data due to an
    auth or network error — the user can paste an ID or press Enter to quit.
    """
    console.print(
        f"  [grey62]Enter the {prompt.lower()} ID manually, or press [bold]Enter[/bold] "
        "to abort.[/grey62]"
    )
    value = _typer.prompt(f"  {prompt} ID", default="").strip()
    if not value:
        console.print(f"\n  [grey62]Aborted — no {prompt.lower()} ID provided.[/grey62]\n")
        raise _typer.Exit(4)
    return value


def _make_table(*columns: tuple[str, str, dict[str, Any] | None]) -> Table:
    """Create a consistently styled picker table."""
    tbl = Table(
        header_style=f"bold {PRIMARY}",
        border_style=PRIMARY,
        box=None,
        show_edge=False,
    )
    tbl.add_column("#", style="grey62", width=4, justify="right")
    for name, style, extra in columns:
        tbl.add_column(name, style=style, **(extra or {}))
    return tbl




def pick_person(client: KolayClient | None = None, status: str = "active") -> str:
    """Interactive employee picker."""
    _PERSON_LIMIT = 30

    def fetch(c: KolayClient) -> list[dict[str, Any]]:
        resp = c.post("v2/person/list", data={"page": 1, "limit": _PERSON_LIMIT, "status": status})
        data = resp.get("data", {})
        return data.get("items", data) if isinstance(data, dict) else data

    def fetch_more(c: KolayClient, new_limit: int) -> list[dict[str, Any]]:
        resp = c.post("v2/person/list", data={"page": 1, "limit": new_limit, "status": status})
        data = resp.get("data", {})
        return data.get("items", data) if isinstance(data, dict) else data

    def make_table(items: list[dict[str, Any]]) -> Table:
        tbl = _make_table(
            ("Name", "bold white", {"min_width": 20}),
            ("Title", "cyan", {}),
            ("Department", "cyan", {}),
            ("Email", "grey85", {}),
            ("Short ID", "grey62", {"no_wrap": True}),
        )
        for i, p in enumerate(items, 1):
            name = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() or "—"
            title = p.get("title", "") or "—"
            dept = p.get("department", "") or "—"
            email = p.get("workEmail") or p.get("email") or "—"
            tbl.add_row(str(i), name, title, dept, email, short_id(str(p.get("id", ""))))
        return tbl

    def confirm(p: dict[str, Any]) -> str:
        return f"Selected [bold]{p.get('firstName', '')} {p.get('lastName', '')}[/bold]"

    search_keys = [
        lambda p: f"{p.get('firstName', '')} {p.get('lastName', '')}",
        lambda p: p.get("workEmail") or p.get("email") or "",
    ]
    return _base_pick(
        client, _PICKER_QUIPS, "Colleague", fetch, make_table, confirm, search_keys,
        fetch_more_fn=fetch_more, limit_hint=_PERSON_LIMIT,
    )


def pick_leave(client: KolayClient | None = None) -> str:
    """Interactive leave record picker."""
    from datetime import datetime

    def fetch(c: KolayClient) -> list[dict[str, Any]]:
        now = datetime.now()
        params = {
            "startDate": f"{now.year - 1}-01-01 00:00:00",
            "endDate": f"{now.year}-12-31 23:59:59",
            "limit": 15,
        }
        items: list[dict[str, Any]] = []
        for status in ("approved", "waiting"):
            try:
                resp = c.get("v2/leave/list", params={**params, "status": status})
                data = resp.get("data", [])
                items.extend(data if isinstance(data, list) else data.get("items", []))
            except (APIError, OSError):
                pass  # nosec B110 — picker silences individual status-page errors gracefully
        return items

    def make_table(items: list[dict[str, Any]]) -> Table:
        tbl = _make_table(
            ("Employee", "bold white", {"min_width": 18}),
            ("Type", "grey85", {}),
            ("Start", "grey62", {}),
            ("Status", "grey62", {}),
            ("Short ID", "grey62", {"no_wrap": True}),
        )
        for i, lv in enumerate(items, 1):
            p = lv.get("person", {})
            pname = p.get("name", "—") if isinstance(p, dict) else "—"
            ltype = lv.get("leaveType", {})
            tname = ltype.get("name", "—") if isinstance(ltype, dict) else str(ltype)
            tbl.add_row(
                str(i), pname, tname,
                fmt_datetime(lv.get("startDate")),
                display_status(str(lv.get("status", ""))),
                short_id(str(lv.get("id", ""))),
            )
        return tbl

    def confirm(lv: dict[str, Any]) -> str:
        p = lv.get("person", {})
        pname = p.get("name", "leave record") if isinstance(p, dict) else "leave record"
        return f"Opened [bold]{pname}[/bold]'s leave record"

    search_keys = [
        lambda lv: (lv.get("person") or {}).get("name") or "",
        lambda lv: (lv.get("leaveType") or {}).get("name") or "",
    ]
    return _base_pick(client, _LEAVE_PICKER_QUIPS, "Leave", fetch, make_table, confirm, search_keys)


def pick_transaction(client: KolayClient | None = None) -> str:
    """Interactive transaction picker."""
    from datetime import datetime

    def fetch(c: KolayClient) -> list[dict[str, Any]]:
        now = datetime.now()
        items: list[dict[str, Any]] = []
        for status in ("waiting", "approved"):
            try:
                resp = c.post("v2/transaction/list", data={
                    "startDate": f"{now.year - 1}-01-01 00:00:00",
                    "endDate": f"{now.year}-12-31 23:59:59",
                    "limit": 15, "status": status,
                })
                data = resp.get("data", {})
                batch = data.get("items", data) if isinstance(data, dict) else data
                if isinstance(batch, list):
                    items.extend(batch)
            except (APIError, OSError):
                pass  # nosec B110 — picker silences individual status-page errors gracefully
        return items

    def make_table(items: list[dict[str, Any]]) -> Table:
        tbl = _make_table(
            ("Employee", "bold white", {"min_width": 18}),
            ("Type", "grey85", {}),
            ("Amount", "bold white", {"justify": "right"}),
            ("Status", "grey62", {}),
            ("Short ID", "grey62", {"no_wrap": True}),
        )
        for i, trx in enumerate(items, 1):
            p = trx.get("person", {})
            pname = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() if isinstance(p, dict) else "—"
            amt = trx.get("amount") or trx.get("totalAmount") or "—"
            curr = trx.get("currency", "")
            amt_str = f"{fmt_num(amt)} {curr}".strip() if amt != "—" else "—"
            tbl.add_row(
                str(i), pname, str(trx.get("type", "—")), amt_str,
                display_status(str(trx.get("status", ""))),
                short_id(str(trx.get("id", ""))),
            )
        return tbl

    def confirm(trx: dict[str, Any]) -> str:
        return f"Selected [bold]{trx.get('type', 'transaction')}[/bold] record"

    search_keys = [
        lambda t: f"{(t.get('person') or {}).get('firstName', '')} {(t.get('person') or {}).get('lastName', '')}",
        lambda t: str(t.get("type") or ""),
    ]
    return _base_pick(client, _TRX_PICKER_QUIPS, "Transaction", fetch, make_table, confirm, search_keys)


def pick_event(client: KolayClient | None = None) -> str:
    """Interactive calendar event picker."""
    from datetime import datetime, timedelta

    def fetch(c: KolayClient) -> list[dict[str, Any]]:
        now = datetime.now()
        resp = c.get("v2/event/list", params={
            "start": (now - timedelta(days=90)).strftime("%Y-%m-%d 00:00:00"),
            "end": (now + timedelta(days=365)).strftime("%Y-%m-%d 23:59:59"),
            "limit": 20, "page": 1,
        })
        data = resp.get("data", {})
        return data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

    def make_table(items: list[dict[str, Any]]) -> Table:
        tbl = _make_table(
            ("Title", "bold white", {"min_width": 24}),
            ("Start", "grey85", {}),
            ("Short ID", "grey62", {"no_wrap": True}),
        )
        for i, ev in enumerate(items, 1):
            tbl.add_row(
                str(i), str(ev.get("title", "—")),
                fmt_datetime(ev.get("start")),
                short_id(str(ev.get("id", ""))),
            )
        return tbl

    def confirm(ev: dict[str, Any]) -> str:
        return f"Selected [bold]{ev.get('title', 'event')}[/bold]"

    search_keys = [
        lambda ev: str(ev.get("title") or ""),
    ]
    return _base_pick(client, _EVENT_PICKER_QUIPS, "Event", fetch, make_table, confirm, search_keys)


def pick_timelog(client: KolayClient | None = None) -> str:
    """Interactive timelog picker."""
    from datetime import datetime

    def fetch(c: KolayClient) -> list[dict[str, Any]]:
        now = datetime.now()
        resp = c.post("v2/timelog/list", data={
            "page": 1, "limit": 20,
            "startDate": f"{now.year - 1}-01-01 00:00:00",
            "endDate": f"{now.year}-12-31 23:59:59",
            "sortType": "startDate", "sortOrder": "desc",
        })
        data = resp.get("data", {})
        return data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

    def make_table(items: list[dict[str, Any]]) -> Table:
        tbl = _make_table(
            ("Employee", "bold white", {"min_width": 18}),
            ("Type", "grey85", {}),
            ("Start", "grey62", {}),
            ("Status", "grey62", {}),
            ("Short ID", "grey62", {"no_wrap": True}),
        )
        for i, tl in enumerate(items, 1):
            p = tl.get("person", {})
            pname = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() if isinstance(p, dict) else "—"
            tbl.add_row(
                str(i), pname, str(tl.get("type", "—")),
                fmt_datetime(tl.get("startDate")),
                display_status(str(tl.get("status", ""))),
                short_id(str(tl.get("id", ""))),
            )
        return tbl

    def confirm(tl: dict[str, Any]) -> str:
        p = tl.get("person", {})
        pname = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() if isinstance(p, dict) else ""
        label_str = f"{pname}'s {tl.get('type', 'timelog')}" if pname else str(tl.get("type", "timelog"))
        return f"Selected [bold]{label_str}[/bold]"

    search_keys = [
        lambda tl: f"{(tl.get('person') or {}).get('firstName', '')} {(tl.get('person') or {}).get('lastName', '')}",
        lambda tl: str(tl.get("type") or ""),
    ]
    return _base_pick(client, _TIMELOG_PICKER_QUIPS, "Timelog", fetch, make_table, confirm, search_keys)


def pick_training(client: KolayClient | None = None) -> str:
    """Interactive training catalogue picker."""
    _TRAINING_LIMIT = 30

    def fetch(c: KolayClient) -> list[dict[str, Any]]:
        resp = c.get("v2/training/list", params={"page": 1, "limit": _TRAINING_LIMIT})
        data = resp.get("data", {})
        return data.get("items", data) if isinstance(data, dict) else (data if isinstance(data, list) else [])

    def fetch_more(c: KolayClient, new_limit: int) -> list[dict[str, Any]]:
        resp = c.get("v2/training/list", params={"page": 1, "limit": new_limit})
        data = resp.get("data", {})
        return data.get("items", data) if isinstance(data, dict) else (data if isinstance(data, list) else [])

    def make_table(items: list[dict[str, Any]]) -> Table:
        tbl = _make_table(
            ("Training Name", "bold white", {"min_width": 24}),
            ("Duration", "grey85", {"justify": "right"}),
            ("Short ID", "grey62", {"no_wrap": True}),
        )
        for i, tr in enumerate(items, 1):
            dur = tr.get("duration") or tr.get("durationDays") or "—"
            tbl.add_row(str(i), str(tr.get("name", "—")), str(dur), short_id(str(tr.get("id", ""))))
        return tbl

    def confirm(tr: dict[str, Any]) -> str:
        return f"Selected [bold]{tr.get('name', 'training')}[/bold]"

    search_keys = [
        lambda tr: str(tr.get("name") or ""),
    ]
    return _base_pick(
        client, _TRAINING_PICKER_QUIPS, "Training", fetch, make_table, confirm, search_keys,
        fetch_more_fn=fetch_more, limit_hint=_TRAINING_LIMIT,
    )


def pick_person_training(client: KolayClient | None = None, person_id: str | None = None) -> str:
    """Interactive person-training assignment picker."""
    from ..api.client import KolayClient as _Client
    from ..api.errors import APIError

    if client is None:
        try:
            client = _Client()
        except APIError:
            return _typer.prompt("  Training assignment ID")

    if not person_id:
        person_id = pick_person(client)

    def fetch(c: KolayClient) -> list[dict[str, Any]]:
        resp = c.get(f"v2/person/list-trainings/{person_id}")
        data = resp.get("data", [])
        return data if isinstance(data, list) else data.get("items", [])

    def make_table(items: list[dict[str, Any]]) -> Table:
        tbl = _make_table(
            ("Training", "bold white", {"min_width": 22}),
            ("Status", "grey62", {}),
            ("Start", "grey62", {}),
            ("Short ID", "grey62", {"no_wrap": True}),
        )
        for i, pt in enumerate(items, 1):
            t = pt.get("training", {})
            tname = t.get("name", "—") if isinstance(t, dict) else str(t)
            tbl.add_row(
                str(i), tname,
                display_status(str(pt.get("status", ""))),
                fmt_datetime(pt.get("startDate")),
                short_id(str(pt.get("id", ""))),
            )
        return tbl

    def confirm(pt: dict[str, Any]) -> str:
        t = pt.get("training", {})
        tname = t.get("name", "assignment") if isinstance(t, dict) else "assignment"
        return f"Selected [bold]{tname}[/bold] assignment"

    return _base_pick(client, _PERSON_TRAINING_PICKER_QUIPS, "Assignment", fetch, make_table, confirm)


def pick_person_file(client: KolayClient | None = None, person_id: str | None = None) -> str:
    """Interactive person file/folder picker."""
    from ..api.client import KolayClient as _Client
    from ..api.errors import APIError

    if client is None:
        try:
            client = _Client()
        except APIError:
            return _typer.prompt("  Item ID")

    if not person_id:
        person_id = pick_person(client)

    def fetch(c: KolayClient) -> list[dict[str, Any]]:
        resp = c.get(f"v2/person/list-files/{person_id}")
        data = resp.get("data", [])
        return data if isinstance(data, list) else data.get("items", [])

    def make_table(items: list[dict[str, Any]]) -> Table:
        tbl = _make_table(
            ("Name", "bold white", {"min_width": 22}),
            ("Folder", "grey85", {}),
            ("Short ID", "grey62", {"no_wrap": True}),
        )
        for i, f in enumerate(items, 1):
            name = f.get("name") or "—"
            folder = f.get("folderName") or "—"
            tbl.add_row(str(i), name, folder, short_id(str(f.get("id", ""))))
        return tbl

    def confirm(f: dict[str, Any]) -> str:
        return f"Selected item [bold]{f.get('name', 'file')}[/bold]"

    search_keys = [
        lambda f: str(f.get("name") or ""),
        lambda f: str(f.get("folderName") or ""),
    ]
    return _base_pick(client, _FILE_PICKER_QUIPS, "File or Folder", fetch, make_table, confirm, search_keys)
