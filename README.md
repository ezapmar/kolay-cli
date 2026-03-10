
# CLI and MCP server for Kolay IK

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

---

# Disclaimer (Alpha)

1. **Unofficial project.** This is an independent lab application, not a Kolay IK product. Kolay Yazilim A.S. is not responsible for any data loss or issues caused by this software.
2. **Your token, your responsibility.** Generate tokens at [app.kolayik.com/settings/developer-settings](https://app.kolayik.com/settings/developer-settings) and keep them safe.
3. **Write operations are real.** Every create, update, delete, and terminate action modifies live HR data. There is no sandbox.
4. **Alpha software.** Expect bugs. Report them at [GitHub Issues](https://github.com/ezapmar/kolay-cli/issues).

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

### Quick Start — Which setup is right for me?

| I want to… | Method | Time |
|---|---|---|
| Use with ChatGPT, Le Chat, or any web AI | [Public Server (Option 1)](#option-1-use-the-public-server-no-deployment-needed) | 2 min |
| Use with Claude Desktop, Cursor, Gemini CLI | [Local Mode (Option 2)](#option-2-local-mode-stdio) | 1 min |
| Full control, own hosting | [Self-Host (Option 3)](#option-3-self-host-railway--docker) | 15 min |

---

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

---

### Connect from AI Clients (Step-by-Step)

#### ChatGPT (OpenAI)

ChatGPT supports remote MCP servers as **Apps** (formerly called "connectors"). Available on all plans including Plus, Pro, Business, Enterprise, and Education. Requires **Developer Mode** to add custom servers.

> **Important:** ChatGPT connects to *remote* MCP servers only — it cannot run local stdio servers. Your MCP server must be reachable over HTTPS.

**Step 1 — Enable Developer Mode:**

1. Open [chatgpt.com](https://chatgpt.com) → click your profile icon → **Settings**
2. Go to **Apps & Connectors** → scroll to **Advanced settings** (bottom of the page)
3. Toggle **Developer mode** ON
4. You should now see a **Create** button at the top of the Apps & Connectors page

**Step 2 — Create the connector:**

1. In **Settings → Apps & Connectors**, click **Create**
2. Fill in the connector details:
   - **Connector name**: `Kolay IK`
   - **Description**: `HR management — employees, leaves, timelogs, trainings, payroll`
   - **Connector URL**: `https://kolay.up.railway.app/mcp`
3. Click **Create**
4. If the connection succeeds, you'll see a list of tools the server advertises

> **Authentication note:** ChatGPT Apps support OAuth 2.1 for user-level auth. For Kolay IK, the simplest approach is to deploy with `KOLAY_API_TOKEN` set as an environment variable on the server (single-tenant mode), which requires no user-side auth setup. If you need per-user tokens, see the [self-host option](#option-3-self-host-railway--docker).

**Step 3 — Use it in a conversation:**

1. Open a **new chat** in ChatGPT
2. Click the **+** button near the message composer, then click **More**
3. Select **Kolay IK** from the list of available tools
4. Ask a question like `"Show me all active employees"`

ChatGPT will display tool-call payloads so you can confirm inputs and outputs. Write operations require manual confirmation.

> **Tip:** After updating your MCP server, refresh the connector metadata: go to **Settings → Apps & Connectors**, click into your connector, and choose **Refresh**.

📖 *Full docs: [developers.openai.com/apps-sdk/deploy/connect-chatgpt](https://developers.openai.com/apps-sdk/deploy/connect-chatgpt)*

#### Mistral Le Chat

1. Open [chat.mistral.ai](https://chat.mistral.ai) and go to **Intelligence** → **Connectors** (or [chat.mistral.ai/connections](https://chat.mistral.ai/connections))
2. Click **Add Connector** → **Custom MCP Connector**
3. Fill in:
   - **Name**: `Kolay IK`
   - **URL**: `https://kolay.up.railway.app/mcp`
   - **Description** *(optional)*: HR management tools for Kolay IK
4. For authentication, select:
   - **No Authentication** — if the server has `KOLAY_API_TOKEN` set (single-tenant)
   - **HTTP Bearer Token** — enter your Kolay IK API token if using multi-tenant mode
5. Click **Connect**
6. In any chat, make sure the Kolay IK connector is enabled (toggle it on in the connectors panel)

Now ask Le Chat:

```
Who are the employees in the engineering department?
```

> **Tip:** Le Chat auto-detects available tools from the MCP server. You don't need to configure individual tools.

#### Claude Desktop

**Automatic (recommended):**

```bash
kolay mcp install
```

This writes the correct config to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows). Restart Claude Desktop.

**Manual:**

1. Open Claude Desktop → **Settings** → **Developer** → **Edit Config**
2. Add the following to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kolay-ik": {
      "command": "kolay-mcp",
      "args": []
    }
  }
}
```

3. Save and restart Claude Desktop
4. You should see "kolay-ik" in the MCP servers list (🔌 icon)

**Remote mode (no local install):**

1. In Claude Desktop → **Settings** → **Connectors** → **Add custom connector**
2. Enter URL: `https://kolay.up.railway.app/mcp`
3. Optionally add your `X-Kolay-Token` in the URL as a query parameter or configure the Authorization header

#### Cursor

**Automatic:**

```bash
kolay mcp install
```

**Manual (global):** Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "kolay-ik": {
      "command": "kolay-mcp",
      "args": []
    }
  }
}
```

**Manual (project-level):** Create `.cursor/mcp.json` in your project root with the same content.

Restart Cursor after saving.

#### Gemini CLI

**Automatic:**

```bash
kolay mcp install
```

**Manual:** Edit `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "kolay-ik": {
      "command": "kolay-mcp",
      "args": []
    }
  }
}
```

#### VS Code (GitHub Copilot)

1. Open VS Code → **Settings** (Ctrl+Shift+P → "Preferences: Open User Settings (JSON)")
2. Add to `mcp.servers`:

```json
{
  "mcp": {
    "servers": {
      "kolay-ik": {
        "command": "kolay-mcp",
        "args": []
      }
    }
  }
}
```

3. Alternatively, use the remote URL via the MCP extension settings

#### Windsurf

**Automatic:**

```bash
kolay mcp install
```

**Manual:** Edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "kolay-ik": {
      "command": "kolay-mcp",
      "args": []
    }
  }
}
```

#### Zed

Edit `~/.config/zed/settings.json` and add under `"context_servers"`:

```json
{
  "context_servers": {
    "kolay-ik": {
      "command": {
        "path": "kolay-mcp",
        "args": []
      }
    }
  }
}
```

#### Any Other MCP Client

Any client that supports the MCP standard can connect using either:

- **Remote (HTTP/SSE):** Point to `https://kolay.up.railway.app/mcp` with an `X-Kolay-Token` header
- **Local (stdio):** Run the `kolay-mcp` binary (installed with `pip install kolay-cli`)

---

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

The MCP session always connects successfully. Authentication happens at the **tool level** — every HR tool checks for a valid token before accessing data. This means AI clients can discover available tools before authenticating.

Token resolution order:
1. `X-Kolay-Token` header (per-request, multi-tenant)
2. `Authorization: Bearer <token>` header
3. `KOLAY_API_TOKEN` environment variable (single-tenant fallback)

---

### Available MCP Tools

The server exposes these tools to AI clients:

| Tool | Description |
|---|---|
| `validate_connection` | Check if credentials are working |
| `person_list`, `person_view`, `person_summary` | Read employee data |
| `person_leave_status` | View leave balances for an employee |
| `person_create`, `person_update`, `person_terminate` | Write employee data |
| `person_rehire`, `person_update_fields` | Rehire or patch arbitrary fields |
| `leave_list`, `leave_view`, `leave_create`, `leave_cancel` | Manage leaves |
| `request_time_off` | Natural language leave creation |
| `analyze_leave_impact` | Dry-run balance check before booking leave |
| `timelog_list`, `timelog_view`, `timelog_create`, `timelog_delete` | Manage timelogs |
| `training_list`, `training_view`, `training_create`, `training_delete` | Training catalogue |
| `person_assign_training`, `person_list_trainings`, `person_update_training` | Training assignments |
| `transaction_list`, `transaction_view`, `transaction_create`, `transaction_delete` | Manage payroll |
| `calendar_list`, `calendar_view`, `calendar_create`, `calendar_update`, `calendar_delete` | Manage events |
| `unit_tree` | View organisational structure |
| `approval_list` | View approval workflows |
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
| `hr_capabilities` | Guided prompt explaining all available Kolay HR AI features |

---

### Usage Examples (AI Conversations)

Here are real-world examples of what you can ask any AI assistant connected to Kolay MCP:

#### Listing Employees

```
You: Show me all active employees
AI:  → calls person_list(status="active", limit=20)
     Found 47 employees. Here are the first 20:
     1. Ayşe Yılmaz — Engineering — ayse@company.com
     2. Mehmet Demir — Marketing — mehmet@company.com
     ...
```

#### Searching for Someone

```
You: Find the employee named Ahmet
AI:  → calls person_list(search="Ahmet")
     Found 2 matches:
     1. Ahmet Kaya (ID: abc123) — Engineering
     2. Ahmet Yıldız (ID: def456) — Sales
```

#### Viewing an Employee Profile

```
You: Show me Ayşe Yılmaz's full profile
AI:  → calls person_view(person_id="Ayşe Yılmaz")
     Name: Ayşe Yılmaz
     Department: Engineering
     Start Date: 2023-01-15
     Email: ayse@company.com
     Phone: +90 555 123 4567
     ...
```

#### Checking Leave Balances

```
You: How many days of annual leave does Mehmet have left?
AI:  → calls person_leave_status(person_id="Mehmet Demir")
     Annual Leave: 8.5 days remaining (out of 14)
     Sick Leave: 10 days remaining
     ...
```

#### Requesting Time Off

```
You: I want to take next Monday and Tuesday off as annual leave
AI:  → calls analyze_leave_impact(person_id="...", leave_type_id="...", requested_days=2)
     You have 8.5 days remaining. After this request: 6.5 days.
     Shall I go ahead and submit this?
You: Yes
AI:  → calls request_time_off(person_id="...", leave_type_id="...",
         start_date="2026-03-16", end_date="2026-03-17")
     ✅ Leave request submitted for March 16–17.
```

#### Listing Pending Leaves

```
You: Show me all pending leave requests
AI:  → calls leave_list(status="waiting")
     3 pending requests:
     1. Ayşe Yılmaz — Annual Leave — Mar 20–22
     2. Mehmet Demir — Sick Leave — Mar 18
     3. Zeynep Kara — Annual Leave — Apr 1–5
```

#### Creating a New Employee

```
You: Add a new employee: Ali Veli, ali@company.com, starting April 1st
AI:  ⚠️ This will create a real employee record. Confirm?
You: Yes
AI:  → calls person_create(first_name="Ali", last_name="Veli",
         email="ali@company.com", employment_start="2026-04-01")
     ✅ Employee created: Ali Veli (ID: ghi789)
```

#### Employee Health Check

```
You: Give me a quick health check on Ayşe Yılmaz
AI:  → calls employee_health_check(person_id="Ayşe Yılmaz")
     📋 Upcoming leaves: Annual Leave Mar 20–22
     ⏱️ Recent timelogs: 42h this week (8h overtime)
     📚 Training: "AWS Security" — completed
```

#### Organisation Chart

```
You: Show me the company org chart
AI:  → calls unit_tree()
     🏢 Acme Corp
     ├── 🏗️ Engineering (12 people)
     │   ├── Backend Team (5)
     │   └── Frontend Team (4)
     ├── 📈 Marketing (8 people)
     └── 💰 Finance (5 people)
```

#### Manager Morning Briefing (using prompt)

```
You: Give me a morning briefing for the Engineering department
AI:  → uses manager_dashboard prompt
     📊 Engineering Department — Morning Briefing
     • 2 people on leave today (Ayşe, Mehmet)
     • 1 pending leave request to approve
     • 3 overtime entries logged yesterday
     • Training "Cloud Security 101" starts next week (4 enrolled)
```

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
