# Kolay CLI — Agent Guide

> CLI for [Kolay IK](https://kolayik.com) HR platform. Python 3.9+, Typer + Rich.

## Quick Start

```bash
pip install kolay-cli          # or: pipx install kolay-cli
kolay auth login               # paste your API token
kolay --json person list       # structured output for agents
```

## Agent Flags

| Flag | Effect |
|------|--------|
| `--json` | All output as JSON to stdout, no Rich UI |
| `--yes` / `-y` | Skip all confirmation prompts |

Env var alternative: `KOLAY_OUTPUT=json`

## Command Tree

```
kolay
├── auth     login │ status │ me │ logout
├── config   show │ set │ validate
├── person   list │ view │ create │ update │ terminate │ rehire │ ...
├── leave    list │ view │ create
├── timelog  list │ view │ create │ delete
├── training list │ view │ create │ update │ delete
├── transaction list │ view │ create │ delete
├── calendar list │ view │ create │ update │ delete
├── expense  list
├── payroll  view
├── approval list
└── unit     tree │ create-item
```

Every command supports `kolay <group> <command> --help` for full options.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General / server error |
| 2 | Bad input / validation |
| 3 | Not found |
| 4 | Auth / permission denied |
| 5 | Conflict |

## JSON Error Shape

```json
{"error": true, "message": "...", "status": 401, "hint": "...", "exit_code": 4}
```

## Auth

Token stored at `~/.config/kolay/token`. Set via `kolay auth login` or env `KOLAY_API_TOKEN`.
Base URL: `https://api.kolayik.com` (override with `kolay config set base_url <url>`).

## Testing

```bash
uv run --extra test pytest tests/ -v
```

## Key Patterns

- **List + filter**: `kolay --json person list --search "alice" --status active`
- **View by ID**: `kolay --json person view <uuid>`
- **Delete without prompt**: `kolay --yes training delete <uuid>`
- **Pipe to jq**: `kolay --json leave list | jq '.[] | select(.status=="approved")'`
