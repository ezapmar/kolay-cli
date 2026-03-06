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

A production-ready command-line interface and MCP server for the [Kolay IK API](https://apidocs.kolayik.com).
Manage employees, leaves, timelogs, transactions, calendar events, and more — from your terminal or through AI assistants.

<img width="1283" height="609" alt="Kolay CLI" src="https://github.com/user-attachments/assets/eec257a1-68c0-43fa-967c-169ba1fcaf6d" />

---

## Installation

```bash
pipx install kolay-cli
```

Or with pip:

```bash
pip install kolay-cli
```

With MCP/AI integration support:

```bash
pip install 'kolay-cli[mcp]'
```

> **Recommended**: Use `pipx` to install CLI tools in isolated environments.

---

## Getting Started

### 1. Authenticate

```bash
kolay auth login
```

You will be prompted for your Kolay API token. It is stored at `~/.config/kolay/config.json` with `0600` permissions.

### 2. Verify your session

```bash
kolay auth status
kolay auth me
```

### 3. Explore

```bash
kolay              # logo + full command list
kolay person list  # list active employees
kolay --help       # grouped command reference
```

---

## Commands

### Authentication

| Command | Description |
|---|---|
| `kolay auth login` | Save and verify your API token |
| `kolay auth status` | Show login status and user name |
| `kolay auth me` | Show your full profile |

### Configuration

| Command | Description |
|---|---|
| `kolay config show` | Display active config (source: env / file) |
| `kolay config set <key> <value>` | Write a config key to the config file |
| `kolay config validate` | Ping the API to verify your token is valid |

**Valid keys:** `api_token`, `base_url`

### People

| Command | Description |
|---|---|
| `kolay person list` | List active employees |
| `kolay person list --status inactive` | List terminated employees |
| `kolay person list --search "ali"` | Search by name or email |
| `kolay person view <id>` | Full profile of an employee |
| `kolay person summary <id>` | Quick profile summary |
| `kolay person create` | Create a new employee record |
| `kolay person update <id>` | Update profile fields |
| `kolay person leave-status <id>` | View leave balances |
| `kolay person list-files <id>` | List attached documents |
| `kolay person list-trainings <id>` | List assigned trainings |
| `kolay person assign-training` | Assign a training to an employee |
| `kolay person update-training <id>` | Update training status/dates |
| `kolay person delete-training <id>` | Remove a training assignment |
| `kolay person fields` | List all available person field tokens |
| `kolay person bulk-view <ids>` | View multiple profiles at once |
| `kolay person terminate <id>` | Terminate an employee |

### Leave

| Command | Description |
|---|---|
| `kolay leave list` | List approved leave records |
| `kolay leave list --status waiting` | Show pending requests |
| `kolay leave list --person-id <id>` | Filter by employee |
| `kolay leave view [id]` | View a specific leave record |
| `kolay leave create` | Create a new leave request |

### Timelogs

| Command | Description |
|---|---|
| `kolay timelog list` | List timelog records |
| `kolay timelog list --type overtime` | Filter by type |
| `kolay timelog list --status waiting` | Filter by approval status |
| `kolay timelog view [id]` | View a specific timelog |
| `kolay timelog create` | Create a new timelog entry |
| `kolay timelog delete [id]` | Delete a timelog |

### Training Catalogue

| Command | Description |
|---|---|
| `kolay training list` | List all training courses |
| `kolay training list --search "fire"` | Search by name |
| `kolay training view [id]` | View training details |
| `kolay training create` | Add a training to the catalogue |
| `kolay training update [id]` | Update a training record |
| `kolay training delete [id]` | Remove a training from the catalogue |

### Transactions

| Command | Description |
|---|---|
| `kolay transaction list` | List all transactions |
| `kolay transaction list --type bonus` | Filter by type |
| `kolay transaction list --status waiting` | Filter by approval status |
| `kolay transaction view [id]` | View a specific transaction |
| `kolay transaction create` | Create a new transaction |
| `kolay transaction delete [id]` | Delete a transaction |

**Supported types:** `expense`, `advancePayment`, `bonus`, `premium`, `otherCut`, `militaryBenefit`, `nationalHolidayBenefit`, `fuelAllowanceBenefit`

### Expense Categories

| Command | Description |
|---|---|
| `kolay expense categories` | List expense categories |
| `kolay expense categories --enabled` | Show only active categories |
| `kolay expense categories --title "taxi"` | Filter by title |

### Approvals

| Command | Description |
|---|---|
| `kolay approval list` | List configured approval processes |

### Calendar

| Command | Description |
|---|---|
| `kolay calendar list` | List events for the next 30 days |
| `kolay calendar list --start 2026-01-01 --end 2026-12-31` | Date range filter |
| `kolay calendar list --search "meeting"` | Search by title |
| `kolay calendar view [id]` | View event details |
| `kolay calendar create` | Create a new event |
| `kolay calendar update [id]` | Update an event |
| `kolay calendar delete [id]` | Delete an event |

### Organisation Units

| Command | Description |
|---|---|
| `kolay unit tree` | Show the full organisational tree |
| `kolay unit create-item` | Add an item to a unit |

### MCP Server (AI/LLM Integration)

| Command | Description |
|---|---|
| `kolay mcp serve` | Start the MCP server (STDIO, for Claude Desktop / Cursor / Gemini CLI) |
| `kolay mcp serve --transport http` | Start as an HTTP endpoint for network access |
| `kolay mcp tools` | List all 31 registered MCP tools |

> Requires `pip install 'kolay-cli[mcp]'`

---

## Interactive Selection

Any command that takes an ID supports interactive selection. Omit the ID to get a live search-and-pick menu:

```bash
kolay leave view          # pick from recent leave records
kolay timelog delete      # pick from recent timelogs
kolay training update     # pick from the catalogue
```

---

## Error Handling

Errors are never raw tracebacks. Every failure renders a branded panel:

- **401 Unauthorized** — witty analogy + exact fix (`kolay auth login`)
- **403 Forbidden** — friendly "wrong floor" message + admin contact hint
- **429 Too Many Requests** — "slow down" message with retry guidance
- **500 Server Error** — "the server sneezed" with retry suggestion
- **Other errors** — plain panel with message and recovery hint

Bare command groups (`kolay auth`, `kolay person`, etc.) show a hint and automatically display help after a 3-second countdown — instead of the generic "Missing command" error.

---

## Configuration

### API Token

Interactive login (stores token in `~/.config/kolay/config.json`):
```bash
kolay auth login
```

Via environment variable (takes precedence over the config file):
```bash
export KOLAY_API_TOKEN=your_token_here
```

Via config command:
```bash
kolay config set api_token your_token_here
kolay config validate
```

### Base URL

Default: `https://api.kolayik.com`. Override:
```bash
export KOLAY_BASE_URL=https://custom.domain.com
# or
kolay config set base_url https://custom.domain.com
```

> HTTPS is mandatory. HTTP base URLs are rejected at startup.

### Config File Location

```
~/.config/kolay/config.json
```

File permissions: `0600` (owner read/write only).

### Debug Logging

```bash
kolay --debug person list
```

Writes full HTTP request/response cycles to `~/.config/kolay/debug.log`. Hidden from normal output.

---

## MCP Server (AI/LLM Integration)

Kolay CLI includes a built-in [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server powered by [FastMCP](https://gofastmcp.com). This lets AI assistants and LLMs interact with Kolay IK directly.

### Quick Start

```bash
# Install with MCP support
pip install 'kolay-cli[mcp]'

# List available tools
kolay mcp tools

# Start the server (STDIO mode)
kolay mcp serve
```

### Claude Desktop / Cursor / Gemini CLI

Add to `~/.claude/claude_desktop_config.json`:

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

### HTTP Mode

Expose as a network endpoint for multi-client or remote access:

```bash
kolay mcp serve --transport http --port 8000
```

### Available Tools (31)

The MCP server exposes tools across all Kolay IK domains:

| Domain | Tools |
|---|---|
| People | `person_list`, `person_view`, `person_summary`, `person_leave_status`, `person_create`, `person_update`, `person_terminate`, `person_rehire`, `person_assign_training` |
| Leave | `leave_list`, `leave_view`, `leave_create` |
| Timelogs | `timelog_list`, `timelog_view`, `timelog_create`, `timelog_delete` |
| Training | `training_list`, `training_view`, `training_create`, `training_delete` |
| Transactions | `transaction_list`, `transaction_view`, `transaction_create`, `transaction_delete` |
| Calendar | `calendar_list`, `calendar_view`, `calendar_create`, `calendar_update`, `calendar_delete` |
| Organisation | `unit_tree`, `approval_list` |

### Architecture

Both the CLI and MCP server share a common `services/` layer — zero logic duplication:

```
  CLI (Typer)         MCP (FastMCP)
  commands/*          mcp_server.py
       \                  /
        +--- services/ ---+     pure business logic
                |
           api/client.py        HTTP calls
```

---

## Shell Auto-completion

```bash
# Zsh
kolay --install-completion zsh

# Bash
kolay --install-completion bash
```

After installation, restart your shell or run `source ~/.zshrc`.

---

## Security

- **HTTPS enforced** — HTTP base URLs are rejected at startup to prevent Bearer token leakage over plaintext
- **Token storage** — config file created atomically with `0o600` permissions; no race window
- **No token echo** — login prompt uses `hide_input=True`; token is never printed
- **Input sanitization** — all user-supplied IDs validated against `[a-zA-Z0-9_-]` before URL interpolation; path traversal (`../../`) blocked
- **Endpoint sanitization** — API client rejects endpoints containing `..`, absolute paths, or embedded `://` schemes
- **Request timeouts** — all HTTP calls have a 30-second timeout
- **Error sanitization** — no raw HTTP response bodies or stack traces shown to the user
- **Dependency pinning** — `setuptools>=78.1.1` to avoid known CVEs in older build toolchains
- **Bandit clean** — `bandit -r src/` reports 0 High, 0 Medium, 0 Low issues

---

## Development

```bash
git clone https://github.com/ezapmar/kolay-cli
cd kolay-cli
uv sync
kolay --version
```

### Run tests

```bash
uv run pytest tests/ -v
```

204 tests covering API client, all command modules, services layer, UI helpers, witty error rendering, and the `no_command_help` countdown.

### Security audit

```bash
uv run bandit -r src/ -f screen
```

### Code style

```bash
uv run ruff check src/
uv run mypy src/
```

---

## License

MIT — see [LICENSE](LICENSE).

---

## Links

- [Kolay IK API Documentation](https://apidocs.kolayik.com)
- [GitHub Repository](https://github.com/ezapmar/kolay-cli)
- [PyPI Package](https://pypi.org/project/kolay-cli/)
- [Report an Issue](https://github.com/ezapmar/kolay-cli/issues)
