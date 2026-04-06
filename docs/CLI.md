<!-- =========================================================================
     docs/CLI.md — Kolay CLI reference
     =========================================================================
     MAINTENANCE POLICY
     Append new commands or options to the relevant section.
     Do not rewrite existing sections unless a fact has changed.
     ========================================================================= -->

# Kolay CLI

Command-line interface for [Kolay IK](https://kolayik.com).
Manage employees, leaves, timelogs, trainings, payroll, and organizational
structure directly from the terminal.

> **Disclaimer.** This is an independent project, not an official Kolay Yazilim A.S. product.
> All write operations target live HR data. There is no sandbox.
> You are responsible for your API token and all actions performed.

---

## Table of Contents

- [Installation](#installation)
- [Initial Setup](#initial-setup)
- [Command Reference](#command-reference)
- [Output Modes](#output-modes)
- [Interactive Features](#interactive-features)
- [Security](#security)
- [Shell Completion](#shell-completion)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Exit Codes](#exit-codes)

---

## Installation

### Prerequisites

- Python 3.10 or later
- pip, pipx, or uv

### Install

```bash
# recommended — isolated environment, no conflicts
pipx install kolay-cli

# alternative — plain pip
pip install kolay-cli

# alternative — uv
uv tool install kolay-cli
```

This installs two commands:

| Command | Purpose |
|---------|---------|
| `kolay` | Interactive CLI for terminal use |
| `kolay-mcp` | MCP server binary (see [MCP.md](MCP.md)) |

### Upgrade

```bash
pipx upgrade kolay-cli
# or
pip install --upgrade kolay-cli
```

### Uninstall

```bash
pipx uninstall kolay-cli
# or
pip uninstall kolay-cli
```

---

## Initial Setup

### Guided Setup (Recommended)

```bash
kolay setup
```

This walks you through:
1. Entering your API token (stored in the OS keychain when available).
2. Installing shell autocompletion.
3. Running a health check.

### Manual Setup

```bash
# authenticate
kolay auth login

# verify
kolay doctor
```

### Where to Get a Token

Generate an API token at:
[app.kolayik.com → Settings → API Tokens](https://app.kolayik.com/settings/developer-settings)

---

## Command Reference

All commands follow the pattern `kolay <resource> <action>`. Every command supports `--help`.

### People

```bash
kolay person list                                 # list active employees
kolay person list --limit 50                      # change page size
kolay person list --search "Ahmet"                # search by name or email
kolay person list --status inactive               # list terminated employees

kolay person view <id>                            # view full profile
kolay person view 3                               # view by row number from last list
kolay person summary <id>                         # condensed summary

kolay person create --first-name "Ayse" \
  --last-name "Yilmaz" --email "ayse@co.com" \
  --start-date 2026-04-01                         # create employee

kolay person update <id> --first-name "Ayse"      # update a field
kolay person terminate <id> --date 2026-03-31 \
  --reason 03                                     # terminate
kolay person rehire <id> --start-date 2026-04-01  # rehire

kolay person fields                               # show available custom fields
kolay person list-files <id>                      # list attached documents
kolay person upload-file -p <id> -f ./doc.pdf     # upload a document
kolay person delete-file <file-id>                # delete a document
kolay person bulk-view id1,id2,id3                # view multiple at once
```

### Leaves

```bash
kolay leave list                                  # list approved leaves
kolay leave list --status waiting                 # list pending leaves
kolay leave list --person-id <id>                 # filter by person
kolay leave view <id>                             # view a single leave

kolay leave create --person-id <id> \
  --type-id <leave-type-uuid> \
  --start 2026-04-10 --end 2026-04-12             # submit leave request
kolay leave cancel <id>                           # cancel a leave
```

### Timelogs

```bash
kolay timelog list                                # list recent timelogs
kolay timelog view <id>                           # view single timelog

kolay timelog create --person-id <id> \
  --start "2026-03-10 18:00:00" \
  --end "2026-03-10 21:00:00" --type overtime     # create entry
kolay timelog delete <id>                         # delete timelog
```

### Trainings

```bash
kolay training list                               # list training catalogue
kolay training view <id>                          # view a training
kolay training create --name "Safety" \
  --duration 4                                    # add to catalogue
kolay training update <id> --name "Fire Safety"   # update
kolay training delete <id>                        # delete from catalogue

kolay training assign --person-id <id> \
  --training-id <training-uuid>                   # assign to employee
kolay person list-trainings <person-id>           # list assignments
```

### Transactions and Payroll

```bash
kolay transaction list                            # list transactions
kolay transaction view <id>                       # view single transaction
kolay transaction create --person-id <id> \
  --type bonus --amount 5000 --date 2026-03-01    # create
kolay transaction delete <id>                     # delete

kolay payroll view <payroll-run-id>               # view payroll sheet
kolay payroll view <id> --search "Ahmet"          # search within
kolay payroll view <id> --filter "Engineering"    # client-side filter
```

### Calendar and Organization

```bash
kolay calendar list                               # list events
kolay calendar list --start 2026-03-01 \
  --end 2026-03-31                                # date range
kolay calendar view <id>                          # view event
kolay calendar create --title "Town Hall" \
  --start "2026-04-15 10:00:00" \
  --end "2026-04-15 11:00:00"                     # create event
kolay calendar update <id> --title "New Title"    # update
kolay calendar delete <id>                        # delete

kolay unit tree                                   # organisational chart
kolay unit tree --filter "Engineering"            # search units
kolay unit create-item --name "Amsterdam" \
  --unit-id <id>                                  # add item to unit

kolay approval list                               # approval workflows
kolay expense categories                          # expense categories
```

### Diagnostics

```bash
kolay doctor                                      # full health check
kolay auth status                                 # logged-in user info
kolay auth me                                     # current profile
```

---

## Output Modes

| Flag | Effect |
|------|--------|
| `--json` | Machine-readable JSON to stdout (for scripts and AI agents) |
| `--yes` / `-y` | Skip confirmation prompts on destructive actions |
| `--debug` | Enable HTTP trace logging |

```bash
# JSON output piped to jq
kolay --json person list --limit 5 | jq '.items[].firstName'

# delete without confirmation
kolay --yes timelog delete <id>

# environment variable alternative
export KOLAY_OUTPUT=json
```

### JSON Error Shape

When `--json` is active, errors are returned as structured JSON:

```json
{
  "error": true,
  "message": "Not found.",
  "status": 404,
  "hint": "Check the ID and try again.",
  "exit_code": 3
}
```

---

## Interactive Features

- **Pickers.** Omit any ID argument and the CLI launches a fuzzy picker to let you select interactively.
- **Row numbers.** After running `kolay person list`, you can use `kolay person view 3` to view the third row directly.
- **Client-side filter.** Most `list` commands support `--filter` to narrow results locally without re-fetching.
- **Smart hints.** Failures include actionable suggestions for recovery, not raw tracebacks.
- **Destructive guards.** Delete and terminate commands require explicit confirmation (bypass with `--yes`).

---

## Security

### Token Storage

Tokens are stored in the OS keychain where available:

| Platform | Backend |
|----------|---------|
| macOS | Keychain |
| Windows | Credential Vault |
| Linux (GUI) | GNOME Keyring / KWallet |
| Linux (headless) | File-backed fallback (`~/.config/kolay/`) with `0o600` permissions |

### Config Encryption at Rest

Enable with `KOLAY_ENCRYPT_CONFIG=true`. The config file is encrypted using AES-256-GCM
with a key derived from machine identity via PBKDF2 (600,000 iterations).
The key is never stored on disk.

### Audit Log

All write operations (POST, PUT, DELETE) are logged to `~/.config/kolay/audit.log`.
The log uses append-only mode with `0o600` permissions and rotates at 5 MB (3 backups).
Each entry is a JSON object with timestamp, method, endpoint, status code, and success flag.

### Network Security

- All API requests require HTTPS. The client rejects non-HTTPS base URLs.
- HTTP traces (via `--debug`) never log response bodies.
- The `Authorization` header is redacted in all debug output.

Full details: [SECURITY.md](SECURITY.md).

---

## Shell Completion

```bash
kolay --install-completion         # install for your current shell
```

Supports bash, zsh, and fish. Restart your terminal after running.
The `kolay setup` wizard offers to do this automatically.

---

## Troubleshooting

### "No API token found"

Run `kolay auth login` or set `KOLAY_API_TOKEN` as an environment variable.

### "Base URL must use HTTPS"

Your `KOLAY_BASE_URL` is set to an HTTP address. Fix it:
```bash
kolay config set base_url https://api.kolayik.com
```

### Token expired

If commands suddenly return 401 errors:
```bash
kolay auth login       # re-authenticate
```

### "Could not connect to the Kolay API"

Check your internet connection. If you are behind a corporate proxy,
configure `HTTPS_PROXY` in your environment.

### Shell completion not working

```bash
kolay --install-completion
```
Then restart your terminal. If it still does not work, check that `kolay` is on your `$PATH`:
```bash
which kolay
```

### Full diagnostic

```bash
kolay doctor
```

This checks: PATH, config file, keyring, token validity, API connectivity, latency,
Python version, shell completion, rate limits, and available updates.

---

## Development

```bash
# install with test and dev extras
pip install -e ".[test,dev]"

# run the full test suite
uv run --extra test pytest tests/ -v

# run a specific test file
uv run --extra test pytest tests/test_person.py -v
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General / server error |
| 2 | Bad input / validation |
| 3 | Not found |
| 4 | Auth / permission denied |
| 5 | Conflict |

---

## License

MIT
