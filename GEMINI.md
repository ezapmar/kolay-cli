# GEMINI.md — Gemini CLI playbook for kolay-cli

## Stack

- Python 3.9+, Typer (on Click), Rich, httpx-compatible requests
- Package manager: `uv` (preferred) or `pip`
- Tests: pytest (`uv run --extra test pytest tests/ -v`)

## Coding Conventions

- `from __future__ import annotations` in every module
- Type hints everywhere, `str | None` style (not `Optional`)
- Commands follow verb-noun: `kolay person list`, `kolay leave create`
- Imports from `..api` for client/errors, `..ui` for formatters/pickers
- **NO EMOJIS.** Do not use Unicode emojis anywhere in the codebase, UI, Slack messages, CLI output, documentation, or comments. Use plain text labels instead.

## Agent Usage

Use `--json` for structured output, `--yes` to bypass confirmations.

```bash
kolay --json person list --limit 10
kolay --json calendar list --start 2025-03-01 --end 2025-03-31
kolay --yes training delete <id>
```

## Exit Codes

`0`=success, `1`=server error, `2`=bad input, `3`=not found, `4`=auth, `5`=conflict.

## Project Layout

```
src/kolay_cli/
├── cli.py              # Entry point, global flags
├── api/
│   ├── client.py       # KolayClient (requests wrapper)
│   └── errors.py       # APIError + semantic exit codes
├── commands/            # One module per resource group
│   ├── person.py, leave.py, timelog.py, ...
└── ui/
    ├── formatters.py    # Rich output, spinner, api_call
    ├── output.py        # JSON mode utilities
    ├── pickers.py       # Interactive ID pickers
    └── search.py        # Client-side filtering
```
