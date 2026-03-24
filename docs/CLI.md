# Kolay CLI Documentation

Command-line interface for [Kolay IK](https://kolayik.com) HR platform. Manage employees, leaves, timelogs, trainings, and payroll directly from your terminal.

---

## Table of Contents

- [Install](#install)
- [Initial Setup](#initial-setup)
- [Command Reference](#command-reference)
  - [People](#people)
  - [Leaves](#leaves)
  - [Timelogs](#timelogs)
  - [Trainings](#trainings)
  - [Transactions and Payroll](#transactions-and-payroll)
  - [Calendar and Organization](#calendar-and-organization)
  - [Fun (Kolay Quiz)](#fun-kolay-quiz)
- [Output Modes](#output-modes)
- [User Experience](#user-experience)
- [Data Security (CLI)](#data-security-cli)
  - [Token Storage](#token-storage)
  - [Config Encryption at Rest](#config-encryption-at-rest)
  - [Network Security](#network-security)
- [Shell Autocompletion](#shell-autocompletion)
- [Development](#development)
- [Exit Codes](#exit-codes)

---

## Install

```bash
# recommended (isolated environment)
pipx install kolay-cli

# or plain pip
pip install kolay-cli
```

This gives you two commands:

| Command | Purpose |
|---|---|
| `kolay` | Interactive CLI for terminal use |
| `kolay-mcp` | MCP server binary (used by AI clients) |

**Requirements:** Python 3.10+

---

## Initial Setup

```bash
# guided first-time setup (token + config in one step)
kolay setup

# or authenticate manually
kolay auth login
```

You need a Kolay IK API token. Generate one at:
[app.kolayik.com/settings/developer-settings](https://app.kolayik.com/settings/developer-settings)

Verify everything works:

```bash
kolay doctor
```

---

## Command Reference

Commands follow a `kolay <resource> <action>` pattern. Every command supports `--help` for full options.

### People

```bash
# list active employees (default: 20 per page)
kolay person list

# list with a limit
kolay person list --limit 50

# search by name
kolay person list --search "Ahmet"

# view a specific employee (interactive picker if no ID given)
kolay person view
kolay person view abc123def456

# create a new employee
kolay person create --first-name "Ayse" --last-name "Yilmaz" \
  --email "ayse@company.com" --start-date 2026-04-01

# terminate an employee
kolay person terminate abc123def456 --date 2026-03-31 --reason 03
```

### Leaves

```bash
# list approved leaves
kolay leave list

# list pending leaves for a specific person
kolay leave list --status waiting --person-id abc123def456

# create a leave request
kolay leave create --person-id abc123def456 --type-id <leave-type-uuid> \
  --start 2026-04-10 --end 2026-04-12

# cancel a leave
kolay leave cancel <leave-id>
```

### Timelogs

```bash
# list recent timelogs
kolay timelog list

# create an overtime entry
kolay timelog create --person-id abc123def456 \
  --start "2026-03-10 18:00:00" --end "2026-03-10 21:00:00" --type overtime

# delete a timelog
kolay timelog delete <timelog-id>
```

### Trainings

```bash
# list training catalogue
kolay training list

# assign a training to an employee
kolay training assign --person-id abc123def456 --training-id <training-uuid>
```

### Transactions and Payroll

```bash
# list all transactions (bonuses, deductions, etc.)
kolay transaction list

# create a bonus record
kolay transaction create --person-id abc123def456 \
  --type bonus --amount 5000 --date 2026-03-01

# view the full payroll sheet
kolay payroll view abc123def456

# search/filter within a payroll run
kolay payroll view abc123def456 --search "Ahmet" --filter "Dev"
```

### Calendar and Organization

```bash
kolay calendar list                       # company calendar events
kolay unit tree                           # organisational chart
kolay approval list                       # approval workflows
kolay expense list                        # expense records
```

### Fun (Kolay Quiz)

```bash
# play a new session
kolay quiz play

# test the UI with mock data (bypasses API)
kolay quiz play --mock

# view your high scores and stats
kolay quiz stats

# check your daily streak
kolay quiz streak
```

---

## Output Modes

| Flag | What it does |
|---|---|
| `--json` | Machine-readable JSON output (for scripts and AI agents) |
| `--yes` | Skip confirmation prompts on destructive actions |
| `--debug` | Log HTTP traces to `~/.config/kolay/debug.log` |

```bash
# pipe JSON output to jq
kolay --json person list --limit 5 | jq '.items[].firstName'

# delete without confirmation prompt
kolay --yes timelog delete <id>

# environment variable alternative for JSON mode
export KOLAY_OUTPUT=json
```

---

## User Experience

This CLI is built with a **People First** philosophy:

- **Interactive Fallbacks.** Every command that needs an ID launches a fuzzy picker if you omit it.
- **Name Resolution.** You can pass a person's name instead of a UUID to most tools. The system resolves it.
- **Smart Hints.** Failures suggest next steps, not stack traces.
- **Structured Error Handling.** With `--json`, every error has a machine-readable shape for automation.
- **Client-Side Filtering.** Most `list` commands support `--filter` to narrow results locally without re-fetching.
- **Rich Visualization.** Tables, status badges, and panels make HR data readable at a glance.

---

## Data Security (CLI)

### Token Storage

The CLI uses a **layered token resolution** strategy. Tokens are checked in this order:

| Priority | Source | Description |
|---|---|---|
| 1 | Environment variable | `KOLAY_API_TOKEN` |
| 2 | OS Keychain | macOS Keychain, GNOME Keyring, Windows Credential Vault |
| 3 | Legacy config file | `~/.config/kolay/config.yaml` (auto-migrated to keychain) |

**Keychain integration:**

- On macOS: tokens are stored in the macOS Keychain via the `keyring` library.
- On Linux: native GNOME/KDE keyring is preferred. If unavailable, `keyrings.alt` (PlaintextKeyring) is automatically activated as a fallback on headless servers.
- On Windows: Windows Credential Vault is used.

When a token is saved to the keychain, any plaintext copy in config files is **automatically removed** to prevent credential sprawl.

```bash
# store a token securely
kolay auth login

# verify where your token lives
kolay auth status

# remove the token
kolay auth logout
```

### Config Encryption at Rest

The config file (`~/.config/kolay/config.yaml` or `.json`) can be **encrypted at rest** using **Fernet (AES-128-CBC + HMAC-SHA256)**.

| Property | Detail |
|---|---|
| Algorithm | Fernet: AES-128-CBC encryption + HMAC-SHA256 authentication |
| Key derivation | PBKDF2-HMAC-SHA256 with 600,000 iterations |
| Key source | Machine identity: `hostname + OS username` |
| Key storage | Derived on-the-fly, **never stored on disk** |
| Backward compatible | Yes. Plaintext configs continue to work |
| Activation | `KOLAY_ENCRYPT_CONFIG=true` |

```bash
# enable config encryption
export KOLAY_ENCRYPT_CONFIG=true

# next write to config will encrypt it automatically
kolay auth login
```

**How it works:**

1. A 32-byte key is derived from `platform.node():getpass.getuser()` using PBKDF2 (600k rounds).
2. The config content is serialized to JSON/YAML, then encrypted with Fernet.
3. The ciphertext is written with `0o600` permissions (owner read/write only).
4. On read, if the file starts with `gAAAAA` (Fernet prefix), it is decrypted transparently.
5. If you move to a different machine, the derived key changes. The CLI warns you and asks to re-authenticate.

**File permissions:** All config files are created with `0o600` (Unix) permissions -- readable and writable only by the file owner. This prevents other users on the same system from reading your credentials.

### Network Security

- All API communication uses **HTTPS** (TLS 1.2+) to the Kolay IK API at `api.kolayik.com`.
- The `--debug` flag writes HTTP traces to a local log file; **response bodies are never logged** in production mode.
- No telemetry or tracking data is sent anywhere.

---

## Shell Autocompletion

Kolay CLI supports shell autocompletion for `bash`, `zsh`, and `fish`:

```bash
kolay --install-completion
```

Restart your shell after running this. The `kolay setup` wizard offers to enable this automatically.

---

## Development

```bash
# install with test dependencies
pip install -e ".[test,dev]"

# run tests
pytest tests/ -v

# or using uv
uv run --extra test pytest tests/ -v
```

---

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | General / server error |
| 2 | Bad input / validation |
| 3 | Not found |
| 4 | Auth / permission denied |
| 5 | Conflict |

**JSON error shape:**

```json
{
  "error": true,
  "message": "...",
  "status": 401,
  "hint": "...",
  "exit_code": 4
}
```

---

## License

MIT
