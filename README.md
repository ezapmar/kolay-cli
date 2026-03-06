# kolay-cli

```
       ##################
      ###            ###
    ####           ####        %%%                       %%%
   ####           ####         %%%                       %%%
  ####           ####          %%%                       %%%
 ####           ####           %%%   %%%%   %%%%%%%%%    %%%    %%%%%%%%%%%  %%%     %%%%
 ####           ###             %%%  %%%%  %%%%%   %%%%   %%%  %%%%%   %%%%%  %%%%    %%%
 ####          #####            %%%%%%%    %%%       %%%  %%%  %%%       %%%   %%%%  %%%%
  ####       ########           %%%%%%%    %%%       %%%  %%%  %%%       %%%    %%%%%%%%
   ####     ####  ####          %%% %%%%   %%%%     %%%%  %%%  %%%%     %%%%     %%%%%%
    ####   ####    ####         %%%   %%%%  %%%%%%%%%%%   %%%   %%%%%%%%%%%%      %%%%
      ### ####      ####        %%%     %%%    %%%%%      %%%      %%%%  %%%      %%%%
       #####          ###                                                       %%%%%
        ##################                                                     %%%%%
```

A command-line interface and MCP server for the [Kolay IK API](https://apidocs.kolayik.com).
Manage employees, leaves, timelogs, training, transactions, calendar events, and org units — from your terminal or through AI assistants.

<img width="1283" height="609" alt="Kolay CLI" src="https://github.com/user-attachments/assets/eec257a1-68c0-43fa-967c-169ba1fcaf6d" />

---

## Quick Start

```bash
pipx install kolay-cli    # install globally
kolay setup               # guided wizard: auth + shell completion + health check
```

> If `kolay: command not found`, run `pipx ensurepath` and restart your terminal.

---

## Commands

Kolay follows a **verb-noun** pattern: `kolay <resource> <action>`.

### Auth & Config

```bash
kolay auth login                     # save token (stored in OS Keychain)
kolay auth logout                    # remove token from keychain + config
kolay auth status                    # login status, token source, profile
kolay config show                    # active config (env / keychain / file)
kolay config set <key> <value>       # set api_token or base_url
kolay doctor                         # health check (PATH, keychain, API, completion)
```

### People

```bash
kolay person list                    # active employees
kolay person list --status inactive  # terminated employees
kolay person list --search "ali"     # search by name or email
kolay person view <id>               # full profile
kolay person summary <id>            # quick summary
kolay person create                  # create employee
kolay person update <id>             # update profile fields
kolay person terminate <id>          # terminate employee
kolay person leave-status <id>       # leave balances
kolay person fields                  # available field tokens
```

### Leave, Timelogs & Transactions

```bash
kolay leave list                     # approved leave records
kolay leave list --status waiting    # pending requests
kolay leave create                   # create leave request

kolay timelog list                   # timelog records
kolay timelog list --type overtime    # filter by type
kolay timelog create                 # create entry
kolay timelog delete [id]            # delete entry

kolay transaction list               # all transactions
kolay transaction list --type bonus  # filter by type
kolay transaction create             # create transaction
kolay transaction delete [id]        # delete transaction
```

### Training, Calendar & Organisation

```bash
kolay training list                  # training catalogue
kolay training list --search "fire"  # search by name
kolay training create                # add to catalogue

kolay calendar list                  # next 30 days
kolay calendar list --start 2026-01-01 --end 2026-12-31
kolay calendar create                # create event

kolay unit tree                      # organisation tree
kolay approval list                  # approval processes
kolay expense categories             # expense categories
```

> **Tip:** Every `view`, `update`, or `delete` command accepts an optional `[id]`. Omit it to get an interactive picker. You can also pass a **row number** from the last `list` output (e.g. `kolay leave view 3`).

---

## Output Modes

```bash
kolay person list                    # rich table (default)
kolay --json person list             # machine-readable JSON
kolay --debug person list            # writes HTTP traces to ~/.config/kolay/debug.log
```

Use `--json` for scripting/CI and `--yes` to bypass confirmations:

```bash
kolay --json person list --limit 10
kolay --yes training delete <id>
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Server / general error |
| `2` | Bad input |
| `3` | Not found |
| `4` | Auth error |
| `5` | Conflict |

---

## Authentication

Tokens are resolved in this order:

1. **`KOLAY_API_TOKEN` env var** — for CI / Docker
2. **OS Keychain** (macOS Keychain / Windows Credential Manager / Linux Secret Service) — for interactive use
3. **Config file** `~/.config/kolay/config.yaml` — legacy fallback

```bash
kolay auth login                     # interactive → stores in keychain
export KOLAY_API_TOKEN=<token>       # env var → highest priority
kolay auth logout                    # removes from keychain + config file
```

**Linux headless / CI:** Use the env var. For desktop keyring support, install with `pip install 'kolay-cli[linux]'`.

**CI/CD example (GitHub Actions):**

```yaml
- name: Run Kolay CLI
  env:
    KOLAY_API_TOKEN: ${{ secrets.KOLAY_API_TOKEN }}
  run: kolay --json person list
```

---

## MCP Server (AI Integration)

Built-in [Model Context Protocol](https://modelcontextprotocol.io) server — lets AI assistants interact with Kolay IK directly through **31 tools** and **4 prompts**.

```bash
kolay mcp tools                      # list all tools
kolay mcp serve                      # start (STDIO mode)
kolay mcp serve --transport http     # HTTP mode for network access
```

### Connect to Claude Desktop / Cursor / Gemini CLI

Add to your MCP config (e.g. `~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kolay-ik": {
      "command": "kolay",
      "args": ["mcp", "serve"]
    }
  }
}
```

### Architecture

Both CLI and MCP share a common `services/` layer — zero logic duplication:

```
  CLI (Typer)         MCP (FastMCP)
  commands/*          mcp_server.py
       \                  /
        +--- services/ ---+     ← pure business logic
                |
           api/client.py        ← HTTP calls
```

### MCP Tools

| Domain | Tools |
|---|---|
| People | `person_list`, `person_view`, `person_summary`, `person_leave_status`, `person_create`, `person_update`, `person_terminate`, `person_rehire`, `person_assign_training` |
| Leave | `leave_list`, `leave_view`, `leave_create` |
| Timelogs | `timelog_list`, `timelog_view`, `timelog_create`, `timelog_delete` |
| Training | `training_list`, `training_view`, `training_create`, `training_delete` |
| Transactions | `transaction_list`, `transaction_view`, `transaction_create`, `transaction_delete` |
| Calendar | `calendar_list`, `calendar_view`, `calendar_create`, `calendar_update`, `calendar_delete` |
| Organisation | `unit_tree`, `approval_list` |

### MCP Prompts

| Prompt | What it does |
|---|---|
| `employee_snapshot` | HR snapshot with ID card, tenure, and unused leave |
| `burnout_analyzer` | Flags employees with >20 days unused leave + drafts email |
| `onboarding_plan` | Welcome email + IT checklist + first-week meeting |
| `offboarding_plan` | Handover checklist + leave payout + exit interview questions |

---

## Security

| Concern | How it's handled |
|---|---|
| Token storage | OS Keychain via `keyring` — never in plaintext |
| Debug logs | `Authorization: Bearer [REDACTED]` — raw token never on disk |
| HTTPS enforced | HTTP base URLs rejected at startup |
| Input validation | IDs checked against `[a-zA-Z0-9_-]`; path traversal blocked |
| MCP auth | All tools wrapped with `@require_auth`; returns structured 401 |
| Config files | `0600` permissions; atomic writes; auto-migrates tokens to keychain |
| Request safety | 30s timeout; exponential backoff on 429/5xx only |

---

## Development

```bash
git clone https://github.com/ezapmar/kolay-cli && cd kolay-cli
uv sync
kolay --version
```

```bash
uv run --extra test pytest tests/ -v     # 267 tests
uv run ruff check src/                   # lint
uv run mypy src/                         # type check
uv run bandit -r src/ -f screen          # security audit
```

### Shell Completion

```bash
kolay --install-completion zsh           # or bash
source ~/.zshrc                          # reload
```

---

## License

MIT — see [LICENSE](LICENSE).

## Links

- [Kolay IK API Docs](https://apidocs.kolayik.com)
- [GitHub](https://github.com/ezapmar/kolay-cli)
- [PyPI](https://pypi.org/project/kolay-cli/)
- [Issues](https://github.com/ezapmar/kolay-cli/issues)
