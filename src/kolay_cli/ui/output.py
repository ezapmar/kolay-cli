"""Output utilities for JSON and machine-readable data."""
from __future__ import annotations

import json
import os
import re
import sys
from contextvars import ContextVar
from typing import Any

# Matches any Rich markup tag, e.g. [bold], [/bold], [#376BFB]
_RICH_TAG = re.compile(r"\[/?[^\]]+\]")


def strip_markup(text: str) -> str:
    """Strip Rich markup tags from a string for plain-text / JSON output."""
    return _RICH_TAG.sub("", text)



_json_mode: ContextVar[bool] = ContextVar("_json_mode", default=False)
_yes_mode: ContextVar[bool] = ContextVar("_yes_mode", default=False)
_format_mode: ContextVar[str] = ContextVar("_format_mode", default="")

def set_json_mode(enabled: bool) -> None:
    _json_mode.set(enabled)

def set_format_mode(fmt: str) -> None:
    _format_mode.set(fmt.lower())
    if fmt:
        _json_mode.set(True)

def set_yes_mode(enabled: bool) -> None:
    _yes_mode.set(enabled)

def get_format() -> str:
    env = os.environ.get("KOLAY_OUTPUT", "").lower()
    if env in ("json", "csv", "tsv"):
        return env
    fmt = _format_mode.get()
    if fmt:
        return fmt
    if _json_mode.get():
        return "json"
    return "table"

def is_json_mode() -> bool:
    """Return True if machine-readable (JSON, CSV, TSV) output is active."""
    return get_format() in ("json", "csv", "tsv")


def is_yes_mode() -> bool:
    """Return True if confirmation bypass is active (``--yes`` flag)."""
    return _yes_mode.get()


def global_to_page_relative(global_row: int, *, page: int, limit: int) -> int:
    """Convert a global 1-based row number to a page-relative 1-based index.

    Example: global row 21, page 2, limit 20  page-relative index 1.
    Returns the original value unchanged when page == 1 (no conversion needed).
    """
    if page <= 1:
        return global_row
    offset = (page - 1) * limit
    return global_row - offset


def resolve_row(value: str, items: list, *, id_key: str = "id", label: str = "item") -> str:
    """Resolve a 1-based row number to the item's ID.

    ``value`` should be a **page-relative** 1-based index.  Use
    ``global_to_page_relative()`` first when the user sees global row numbers.
    """
    if not value.isdigit():
        return value
    import typer as _typer
    idx = int(value)
    if idx < 1:
        from rich.console import Console as _Console
        _Console().print(f"[red]Row numbers start at 1.[/red]")
        raise _typer.Exit(2)
    if idx > len(items):
        from rich.console import Console as _Console
        _Console().print(
            f"[red]No {label} at row {idx}.[/red] "
            f"[grey62]List shows {len(items)} records.[/grey62]"
        )
        raise _typer.Exit(3)
    return str(items[idx - 1].get(id_key) or "")


def require_arg(value: Any, name: str) -> None:
    """Fail fast if a required argument is missing in JSON mode."""
    if value is None and is_json_mode():
        import typer
        json_error(
            f"Missing required argument: --{name}",
            hint=f"Pass --{name} <value> when using --json.",
            exit_code=2,
        )
        raise typer.Exit(2)


def json_output(data: Any, *, stderr_msg: str | None = None) -> None:
    """Write a structured payload to stdout (JSON, CSV, or TSV)."""
    fmt = get_format()
    if fmt in ("csv", "tsv"):
        import csv
        import io
        if isinstance(data, dict):
            if "items" in data and isinstance(data["items"], list):
                items = data["items"]
            else:
                items = [data]
        elif isinstance(data, list):
            items = data
        else:
            items = []
            
        if not items:
            return
            
        def flatten(item):
            flat = {}
            for k, v in item.items():
                if isinstance(v, dict):
                    for subk, subv in v.items():
                        flat[f"{k}.{subk}"] = subv
                elif isinstance(v, list):
                    flat[k] = json.dumps(v, ensure_ascii=False)
                else:
                    flat[k] = v
            return flat
            
        flat_items = [flatten(i) for i in items]
        keys = set()
        for i in flat_items:
            keys.update(i.keys())
        keys = sorted(list(keys))
        
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=keys, delimiter='\t' if fmt == 'tsv' else ',')
        writer.writeheader()
        for i in flat_items:
            writer.writerow(i)
            
        if stderr_msg:
            print(stderr_msg, file=sys.stderr)
        print(out.getvalue(), end="")
        return

    if stderr_msg:
        print(stderr_msg, file=sys.stderr)

    # Use print() rather than sys.stdout.write() so that Typer/Click
    # test runners can capture the output via their I/O wrappers.
    print(json.dumps(data, ensure_ascii=False, default=str))


def json_error(
    message: str,
    *,
    status: int | None = None,
    hint: str | None = None,
    exit_code: int = 1,
) -> None:
    """Write a structured JSON error to stdout."""
    payload: dict[str, Any] = {"error": True, "message": message}
    if status is not None:
        payload["status"] = status
    if hint is not None:
        payload["hint"] = strip_markup(hint)
    payload["exit_code"] = exit_code

    print(json.dumps(payload, ensure_ascii=False, default=str))
