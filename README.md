# Disclaimer (Alpha)

1. **Unofficial project.** This is an independent lab application, not a Kolay IK product. Kolay Yazilim A.S. is not responsible for any data loss or issues caused by this software.
2. **Your token, your responsibility.** Generate tokens at [app.kolayik.com/settings/developer-settings](https://app.kolayik.com/settings/developer-settings) and keep them safe.
3. **Write operations are real.** Every create, update, delete, and terminate action modifies live HR data. There is no sandbox.
4. **Alpha software.** Expect bugs. Report them at [GitHub Issues](https://github.com/ezapmar/kolay-cli/issues).

---

# kolay-cli

```
               ███████████████████████
              ████               ████ 
             ████               ████ 
            ████               ████          ████                             ███ 
           ███                ████           ████                             ███ 
         ████                ███             ████                             ███ 
        ████               ████              ████     █████    █████████      ███     █████████ ████  ████        ████ 
       ████               ████               ████   █████    █████████████    ███    ███████████████   ████      ████ 
      ████               ████                ████  ████     ████       ████   ███   ████       █████    ███     ████ 
       ████             ██████               ████████      ████         ████  ███  ████         ████    ████    ███ 
        ████           ████████              ████████      ████         ████  ███  ████         ████     ████  ████ 
         ████         ███   ████             ████ █████    ████         ████  ███  ████         ████      ████████ 
          ████      ████     ████            ████   ████    █████     █████   ███   █████     ██████       ██████ 
           ████    ████        ███           ████     ████    ███████████     ███     ██████████████        █████ 
             ███  ████          ████                             █████                   ████               ████ 
              ███████            ████                                                                      ████ 
               ███████████████████████                                                                  ██████ 
                █████████████████████                                                                   ███ 
```

CLI and MCP server for [Kolay IK](https://kolayik.com). Manage employees, leaves, timelogs, trainings, and payroll from your terminal or through any AI assistant that supports MCP.

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

## Setup

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

## CLI Usage

Commands follow a `kolay <resource> <action>` pattern.

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

### Transactions (Payroll)

```bash
# list all transactions
kolay transaction list

# create a bonus
kolay transaction create --person-id abc123def456 \
  --type bonus --amount 5000 --date 2026-03-01
```

### Other Resources

```bash
kolay calendar list                       # company calendar events
kolay unit tree                           # organisational chart
kolay approval list                       # approval workflows
kolay expense list                        # expense records
```

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
```

## MCP Server (AI Integration)

`kolay-cli` ships a full [Model Context Protocol](https://modelcontextprotocol.io) server. Any MCP-compatible AI client can manage your HR data through natural language.

### Option 1: Use the Public Server (no deployment needed)

A shared multi-tenant endpoint is available at:

```
https://kolay.up.railway.app/mcp
```

Each user sends their own Kolay IK token via the `X-Kolay-Token` header. No tokens are stored on the server; they are used only for the duration of each request.

**Connect from any MCP client** by setting the URL and passing your token:

```json
{
  "mcpServers": {
    "kolay-ik": {
      "url": "https://kolay.up.railway.app/mcp",
      "headers": {
        "X-Kolay-Token": "YOUR_KOLAY_API_TOKEN"
      }
    }
  }
}
```

### Option 2: Local Mode (stdio)

For AI clients running on your machine (Claude Desktop, Cursor, etc.), the automated installer writes the correct config for you:

```bash
kolay mcp install
```

Restart your AI client after running this. Supported clients:

| Client | Config Location |
|---|---|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Cursor (global) | `~/.cursor/mcp.json` |
| Cursor (project) | `.cursor/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| Gemini CLI | `~/.gemini/settings.json` |
| VS Code (Copilot) | User-level `mcp.json` |
| Zed | `~/.config/zed/settings.json` |

### Option 3: Self-Host (Railway / Docker)

Deploy your own private instance for full control.

1. Push the repo to GitHub
2. Create a Railway project -> **Deploy from GitHub repo**
3. Set environment variables in Railway:

| Variable | Description |
|---|---|
| `KOLAY_API_TOKEN` | Your Kolay IK API token (single-tenant mode) |
| `PYTHONUNBUFFERED` | `1` |
| `MCP_API_KEY` | Optional gateway key for abuse prevention |

4. Enable public networking in Railway settings
5. Your endpoint: `https://<your-app>.up.railway.app/mcp`

Or run locally in HTTP mode:

```bash
export KOLAY_API_TOKEN="your-token"
kolay mcp serve --transport http --port 8000
```

### How Authentication Works

```
AI Client --> POST /mcp --> MCP Handshake (always succeeds)
                                |
                           Tool Call
                                |
                         @require_auth checks token
                           /           \
                     token found     no token
                          |              |
                     Kolay API     401 error to AI
```

The MCP session always connects successfully. Authentication happens at the **tool level** -- every HR tool checks for a valid token before accessing data. This means AI clients can discover available tools before authenticating.

Token resolution order:
1. `X-Kolay-Token` header (per-request, multi-tenant)
2. `Authorization: Bearer <token>` header
3. `KOLAY_API_TOKEN` environment variable (single-tenant fallback)

### Available MCP Tools

The server exposes these tools to AI clients:

| Tool | Description |
|---|---|
| `validate_connection` | Check if credentials are working |
| `person_list`, `person_view`, `person_summary` | Read employee data |
| `person_create`, `person_update`, `person_terminate` | Write employee data |
| `leave_list`, `leave_view`, `leave_create`, `leave_cancel` | Manage leaves |
| `request_time_off` | Natural language leave creation |
| `analyze_leave_impact` | Dry-run balance check before booking leave |
| `timelog_list`, `timelog_create`, `timelog_delete` | Manage timelogs |
| `training_list`, `training_create`, `person_assign_training` | Manage trainings |
| `transaction_list`, `transaction_create`, `transaction_delete` | Manage payroll |
| `calendar_list`, `calendar_create`, `calendar_update` | Manage events |
| `unit_tree` | View organisational structure |
| `employee_health_check` | Cross-reference leaves, timelogs, and trainings in one call |

### MCP Prompts

Built-in prompts guide the AI through complex multi-step workflows:

| Prompt | What it does |
|---|---|
| `employee_snapshot` | Full profile + leave balance report for one employee |
| `burnout_analyzer` | Scan a department for burnout risk based on unused annual leave |
| `onboarding_plan` | Generate welcome email, IT checklist, and meeting schedule for a new hire |
| `offboarding_plan` | Calculate leave payout, handover checklist, and exit interview questions |
| `bulk_update_assistant` | Safe bulk data cleanup with mandatory human confirmation |
| `manager_dashboard` | Morning briefing for a department manager |

### Connect from Mistral Le Chat

1. Go to [chat.mistral.ai/connections](https://chat.mistral.ai/connections)
2. Add a custom connector with URL: `https://kolay.up.railway.app/mcp`
3. Auth: select **No Authentication** (tools handle it via the server's `KOLAY_API_TOKEN`)
4. Start chatting

### Test with curl

```bash
# discover available tools
curl -X POST https://kolay.up.railway.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

## Project Structure

```
src/kolay_cli/
  cli.py              # entry point, global flags
  mcp_server.py       # FastMCP server with all tools and prompts
  security.py         # token storage, validation, @require_auth
  api/
    client.py         # HTTP client (requests + retry)
    errors.py         # APIError + exit codes
  commands/           # one module per resource group
    person.py, leave.py, timelog.py, training.py,
    transaction.py, calendar.py, unit.py, approval.py, ...
  services/           # business logic (used by both CLI and MCP)
  ui/
    formatters.py     # Rich tables, spinners
    output.py         # JSON mode
    pickers.py        # interactive ID selection
    search.py         # client-side filtering
```

## Development

```bash
# install with test dependencies
pip install -e ".[test,dev]"

# run tests
pytest tests/ -v

# or using uv
uv run --extra test pytest tests/ -v
```

## License

MIT
