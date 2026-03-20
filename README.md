
# CLI and MCP Server for Kolay IK

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

CLI and MCP server for [Kolay IK](https://kolayik.com). Manage employees, leaves, timelogs, trainings, and payroll from your terminal — or through any AI assistant that speaks MCP.

---

## Table of Contents

- [Disclaimer (Alpha)](#disclaimer-alpha)
- [Install](#install)
- [Setup](#setup)
- [CLI Usage](#cli-usage)
  - [People](#people)
  - [Leaves](#leaves)
  - [Timelogs](#timelogs)
  - [Trainings](#trainings)
  - [Transactions & Payroll](#transactions--payroll)
  - [Fun (Kolay Quiz)](#fun-kolay-quiz)
  - [Other Resources](#other-resources)
- [User Experience](#user-experience)
- [Output Modes](#output-modes)
- [MCP Server (AI Integration)](#mcp-server-ai-integration)
  - [Quick Start — Which setup is right for me?](#quick-start--which-setup-is-right-for-me)
  - [Option 1: Public Server (no deployment needed)](#option-1-use-the-public-server-no-deployment-needed)
  - [Option 2: Local Mode (stdio)](#option-2-local-mode-stdio)
  - [Option 3: Self-Host (Railway / Docker)](#option-3-self-host-railway--docker)
  - [Proxy Monitoring & Limits](#proxy-monitoring--limits)
  - [MCP Server Architecture](#mcp-server-architecture)
- [Client Setup Guides](#client-setup-guides)
  - [ChatGPT (OpenAI)](#chatgpt-openai)
  - [Perplexity AI](#perplexity-ai)
  - [Mistral Le Chat](#mistral-le-chat)
  - [Claude Desktop](#claude-desktop)
  - [Cursor](#cursor)
  - [Gemini CLI](#gemini-cli)
  - [VS Code (GitHub Copilot)](#vs-code-github-copilot)
  - [Windsurf](#windsurf)
  - [Zed](#zed)
  - [Any Other MCP Client](#any-other-mcp-client)
- [How Authentication Works](#how-authentication-works)
- [Available MCP Tools](#available-mcp-tools)
- [Session Memory Tools](#session-memory-tools)
- [MCP Prompts](#mcp-prompts)
- [Usage Examples (AI Conversations)](#usage-examples-ai-conversations)
- [Test with curl](#test-with-curl)
- [Project Structure](#project-structure)
- [Development](#development)
- [License](#license)

---

## Disclaimer (Alpha)

> **Please read before using.**

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

---

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

---

## Shell Autocompletion

Kolay CLI supports shell autocompletion for `bash`, `zsh`, and `fish`. Run once:

```bash
kolay --install-completion
```

Restart your shell. The `kolay setup` wizard offers to do this automatically.

---

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

### Transactions & Payroll

```bash
# list all transactions (bonuses, deductions, etc.)
kolay transaction list

# create a bonus record
kolay transaction create --person-id abc123def456 \
  --type bonus --amount 5000 --date 2026-03-01

# view the full payroll sheet (Carsaf Bordro) for a run
kolay payroll view abc123def456

# search/filter rows within a payroll run
kolay payroll view abc123def456 --search "Ahmet" --filter "Dev"
```

### Fun (Kolay Quiz)

Take a break and test your knowledge of your colleagues. Renders high-res images in modern terminals (iTerm2, VSCode, WezTerm) or Braille ASCII art in standard terminals.

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

### Other Resources

```bash
kolay calendar list                       # company calendar events
kolay unit tree                           # organisational chart
kolay approval list                       # approval workflows
kolay expense list                        # expense records
```

---

## User Experience

This CLI is built with a **People First** philosophy. No UUIDs hunted. No cold errors.

- **Interactive Fallbacks.** Every command that needs an ID launches a fuzzy picker if you omit it.
- **Name Resolution.** You can pass a person's name instead of a UUID to most MCP tools. The server resolves it.
- **Smart Hints.** A failure suggests next steps, not a stack trace.
- **Structured Error Handling.** With `--json`, every error has a machine-readable shape for automation.
- **Client-Side Filtering.** Most `list` commands support `--filter` to narrow results locally without re-fetching.
- **Rich Visualization.** Tables, status badges, and panels make HR data readable at a glance.

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
```

---

## MCP Server (AI Integration)

`kolay-cli` ships a full [Model Context Protocol](https://modelcontextprotocol.io) server. Any MCP-compatible AI client can manage your HR data through natural language.

### Quick Start — Which setup is right for me?

| I want to… | Method | Time |
|---|---|---|
| Use with ChatGPT, Le Chat, Perplexity, or any web AI | [Public Server (Option 1)](#option-1-use-the-public-server-no-deployment-needed) | 2 min |
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
| `MCP_RATE_LIMIT_ENABLED` | `true` to enable per-token rate limiting |
| `MCP_RATE_LIMIT_PER_MINUTE` | Max tool calls per minute per token (default: 30) |
| `MCP_RATE_LIMIT_PER_HOUR` | Max tool calls per hour per token (default: 500) |

4. Enable public networking in Railway settings
5. Your endpoint: `https://<your-app>.up.railway.app/mcp`

Or run locally in HTTP mode:

```bash
export KOLAY_API_TOKEN="your-token"
kolay mcp serve --transport http --port 8000
```

---

### Proxy Monitoring & Limits

When hosting the MCP proxy, you can enable rate limiting and monitor activities.

#### Rate Limiting (Opt-in)

The proxy supports per-token sliding-window rate limiting. It is tracked by a privacy-safe hash of each Kolay API token. To enable, set the environment variables above.

#### Activity Logging

The proxy outputs structured JSON logs for every tool invocation to `stdout`:

```json
{"ts": "2026-03-17T12:00:00Z", "event": "mcp.tool_call", "token_key": "tok_...a1b2c3d4", "tool": "person_list", "duration_ms": 142.5, "success": true}
```

Response payloads are never logged. Argument values longer than 64 characters are redacted.

---

### MCP Server Architecture

The server runs on [FastMCP 3.x](https://gofastmcp.com) and is hardened for production:

**Middleware stack (in order):**

| Layer | What it does |
|---|---|
| `ErrorHandlingMiddleware` | Masks internal tracebacks — only your explicit error messages reach clients |
| `SlidingWindowRateLimitingMiddleware` | Per-token rate limiting (opt-in, env-configurable) |
| `TimingMiddleware` | Logs duration of every MCP operation |
| `ResponseLimitingMiddleware` | Truncates tool responses larger than 500 KB |
| `PingMiddleware` | 30-second keep-alive for long SSE sessions |
| `PromptToolMiddleware` | Exposes all 10 prompts as callable tools (for clients that only support tools) |
| `ResourceToolMiddleware` | Exposes all resources as callable tools |

**Tool annotations (machine-readable hints to LLM clients):**

Every tool carries `readOnlyHint`, `destructiveHint`, `idempotentHint`, and `openWorldHint` so client-side safety layers can distinguish reads from writes without reading documentation.

**Component tags for filtering:**

Every tool is tagged: `read`, `write`, `destructive`, `admin`, `analytics`, or `wellness`. MCP clients that support tag filtering can expose only the tools appropriate to the current user's role.

**Tool timeouts:**

Long-running analytics tools have enforced timeouts to prevent sessions from hanging:

| Tool | Timeout |
|---|---|
| `team_availability_analysis` | 90 s |
| `turnover_risk_scan` | 90 s |
| `payroll_anomaly_detect` | 45 s |
| `analyze_employee_wellbeing` | 60 s |
| `get_smart_rest_plan` | 60 s |

**Human-in-the-loop confirmation:**

The two highest-risk destructive tools require explicit user confirmation before executing:

- `person_terminate` — shows the employee name and termination date, asks for confirmation
- `training_delete` — shows the training name, asks for confirmation

If the client does not support interactive confirmation (elicitation), the tool refuses to proceed and tells you why.

---

## Client Setup Guides

Step-by-step instructions for connecting Kolay MCP to popular AI clients.

### ChatGPT (OpenAI)

ChatGPT supports remote MCP servers as **Apps**. Available on all plans. Requires **Developer Mode**.

> **Important:** ChatGPT connects to remote MCP servers only. Your MCP server must be reachable over HTTPS.

**Step 1 — Enable Developer Mode:**

1. Open [chatgpt.com](https://chatgpt.com) -> your profile icon -> **Settings**
2. Go to **Apps & Connectors** -> scroll to **Advanced settings**
3. Toggle **Developer mode** ON

**Step 2 — Create the connector:**

1. In **Settings -> Apps & Connectors**, click **Create**
2. Fill in:
   - **Connector name**: `Kolay IK`
   - **Description**: `HR management — employees, leaves, timelogs, trainings, payroll`
   - **Connector URL**: `https://kolay.up.railway.app/mcp`
3. Click **Create**

**Step 3 — Use it:**

1. Open a new chat -> click **+** -> **More** -> select **Kolay IK**
2. Ask: `Show me all active employees`

> **Tip:** After redeploying your server, go to **Settings -> Apps & Connectors** -> your connector -> **Refresh** to reload the tool list.

---

### Perplexity AI

Requires a **Perplexity Pro** or **Enterprise** plan. Remote servers only.

1. Go to [perplexity.ai](https://www.perplexity.ai) -> **Settings** -> **Connectors**
2. Click **+ Custom connector** -> select **Remote**
3. Fill in:
   - **Name**: `Kolay IK`
   - **MCP Server URL**: `https://kolay.up.railway.app/mcp`
   - **Transport**: `Streamable HTTP`
   - **Authentication**: None (single-tenant) or API Key (multi-tenant)
4. Click **Save**
5. Open a new thread, enable the **Kolay IK** connector, and ask away.

---

### Mistral Le Chat

1. Open [chat.mistral.ai](https://chat.mistral.ai) -> **Intelligence** -> **Connectors**
2. Click **Add Connector** -> **Custom MCP Connector**
3. Fill in:
   - **Name**: `Kolay IK`
   - **URL**: `https://kolay.up.railway.app/mcp`
   - **Authentication**: No Authentication (single-tenant) or HTTP Bearer Token (multi-tenant)
4. Click **Connect**
5. In any chat, toggle the Kolay IK connector on and ask.

> **Tip:** Le Chat auto-detects available tools. No per-tool configuration needed.

---

### Claude Desktop

**Automatic (recommended):**

```bash
kolay mcp install
```

This writes the correct config and restarts cleanly.

**Manual:**

1. Open Claude Desktop -> **Settings** -> **Developer** -> **Edit Config**
2. Add to `claude_desktop_config.json`:

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

3. Save and restart Claude Desktop.

**Remote mode (no local install):**

1. Claude Desktop -> **Settings** -> **Connectors** -> **Add custom connector**
2. Enter URL: `https://kolay.up.railway.app/mcp`

> **Note:** Claude Desktop supports user elicitation. When you ask it to terminate an employee, it will pause and ask for your confirmation before executing.

---

### Cursor

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

---

### Gemini CLI

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

---

### VS Code (GitHub Copilot)

1. Open VS Code -> **Settings** (Ctrl+Shift+P -> "Preferences: Open User Settings (JSON)")
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

---

### Windsurf

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

---

### Zed

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

---

### Any Other MCP Client

Any client that supports MCP can connect using either:

- **Remote (HTTP/SSE):** Point to `https://kolay.up.railway.app/mcp` with an `X-Kolay-Token` header
- **Local (stdio):** Run the `kolay-mcp` binary (installed with `pip install kolay-cli`)

---

## How Authentication Works

```
AI Client --> POST /mcp --> MCP Handshake (always succeeds)
                                |
                           Tool Call
                                |
                         @require_auth checks token
                           /           \
                     token found     no token
                          |              |
                     Kolay API     error returned to AI
```

The MCP session always connects. Authentication happens at the **tool level** — every HR tool checks for a valid token before accessing data. AI clients can discover tools without authenticating first.

Token resolution order:
1. `X-Kolay-Token` header (per-request, multi-tenant)
2. `Authorization: Bearer <token>` header
3. `KOLAY_API_TOKEN` environment variable (single-tenant fallback)

---

## Available MCP Tools

The server exposes 53 tools to AI clients.

**Core HR Tools**

| Tool | Tags | Description |
|---|---|---|
| `validate_connection` | read | Check if credentials are working |
| `person_list` | read | List employees with search and filter |
| `person_view` | read | View full employee profile (auto-caches as last_person in session) |
| `person_summary` | read | Compact profile summary |
| `person_leave_status` | read | View leave balances |
| `employee_health_check` | read | Cross-reference leaves, timelogs, and trainings in one call |
| `person_create` | write | Create a new employee |
| `person_update` | write | Update employee fields |
| `person_update_fields` | write | Update arbitrary fields by raw API name |
| `person_rehire` | write | Rehire a terminated employee |
| `person_assign_training` | write | Assign training to an employee |
| `person_update_training` | write | Update a training assignment |
| `person_terminate` | destructive, admin | Terminate employee (requires confirmation) |
| `person_delete_training` | destructive | Remove a training assignment |
| `leave_list` | read | List leave requests |
| `leave_view` | read | View a single leave request |
| `analyze_leave_impact` | read | Dry-run balance check before booking leave |
| `leave_types` | read | List available leave types |
| `leave_create` | write | Submit a leave request |
| `leave_cancel` | destructive | Cancel a leave request |
| `timelog_list` | read | List timelogs |
| `timelog_view` | read | View a single timelog |
| `timelog_create` | write | Create a timelog entry |
| `timelog_delete` | destructive | Delete a timelog |
| `training_list` | read | List training catalogue |
| `training_view` | read | View a single training |
| `person_list_trainings` | read | List training assignments for an employee |
| `person_training_manage` | write | Assign, update, or remove training (unified) |
| `training_create` | write | Add training to the catalogue |
| `training_update` | write | Update a training record |
| `training_delete` | destructive, admin | Delete training and all history (requires confirmation) |
| `transaction_list` | read | List transactions |
| `transaction_view` | read | View a single transaction |
| `payroll_sheet_view` | read | View the full payroll sheet |
| `transaction_create` | write | Create a transaction (bonus, deduction, etc.) |
| `transaction_delete` | destructive | Delete a transaction |
| `calendar_list` | read | List calendar events |
| `calendar_view` | read | View a single event |
| `unit_tree` | read | View the organisational chart |
| `approval_list` | read | List approval workflows |
| `calendar_create` | write | Create a calendar event |
| `calendar_update` | write | Update a calendar event |
| `calendar_delete` | destructive | Delete a calendar event |

**HR Analytics & Wellbeing Engine**

| Tool | Tags | Description |
|---|---|---|
| `team_availability_analysis` | read, analytics | Peak absence days + operational risk for a team |
| `turnover_risk_scan` | read, analytics | Scan employees for burnout and flight risk, ranked by score |
| `payroll_anomaly_detect` | read, analytics | Detect duplicate transactions and statistical outliers |
| `analyze_employee_wellbeing` | read, wellness | Per-employee burnout score, leave gap detection, bridge-day opportunities |
| `get_smart_rest_plan` | read, wellness | Top upcoming rest windows ranked by leave efficiency |
| `quiz_challenge` | read | Generate a Kolay Quiz challenge |

---

## Session Memory Tools

These three tools give the AI explicit, LLM-controlled memory across tool calls within a session. No data is written to disk. Memory clears when the session ends.

| Tool | Description |
|---|---|
| `session_remember(key, value)` | Store a named value — e.g. `session_remember("focus_person", "abc123")` |
| `session_recall(key)` | Retrieve a stored value — e.g. `session_recall("focus_person")` |
| `session_forget(key)` | Remove a stored value |

**Auto-caching.** After every `person_view` call, the server automatically stores `last_person_id`, `last_person_name`, and `last_person_email` in session state. The AI can then call `session_recall("last_person_id")` without the user repeating a UUID.

---

## MCP Prompts

Built-in prompts guide the AI through complex multi-step workflows. All prompts are also exposed as callable tools for clients that only support the tools protocol.

| Prompt | What it does |
|---|---|
| `employee_snapshot` | Full profile + leave balance report for one employee |
| `burnout_analyzer` | Scan a department for burnout risk based on unused annual leave |
| `onboarding_plan` | Welcome email, IT checklist, and meeting schedule for a new hire |
| `offboarding_plan` | Leave payout calculation, handover checklist, and exit interview questions |
| `bulk_update_assistant` | Safe bulk data cleanup with mandatory human confirmation |
| `manager_dashboard` | Morning briefing for a department manager |
| `wellbeing_briefing` | Per-employee wellbeing report with burnout status and smart rest plan |
| `hr_trend_analysis` | Company-wide trend report combining turnover risk and payroll anomalies |
| `risk_brief` | Concise availability and retention risk brief for a department |
| `hr_capabilities` | Guided prompt explaining all available Kolay HR AI features |

---

## Usage Examples (AI Conversations)

Real-world examples of what you can ask any connected AI assistant.

#### Listing Employees

```
You: Show me all active employees
AI:  -> calls person_list(status="active", limit=20)
     Found 47 employees. Here are the first 20:
     1. Ayse Yilmaz — Engineering
     2. Mehmet Demir — Marketing
     ...
```

#### Searching for Someone

```
You: Find the employee named Ahmet
AI:  -> calls person_list(search="Ahmet")
     Found 2 matches:
     1. Ahmet Kaya (ID: abc123) — Engineering
     2. Ahmet Yildiz (ID: def456) — Sales
```

#### Viewing an Employee Profile

```
You: Show me Ayse Yilmaz's full profile
AI:  -> calls person_view(person_id="Ayse Yilmaz")
     Name: Ayse Yilmaz
     Department: Engineering
     Start Date: 2023-01-15
     Email: ayse@company.com
     ...
     (Session updated: last_person_id = abc-123, last_person_name = Ayse Yilmaz)
```

#### Cross-Tool Reuse via Session Memory

```
You: Now show me her leave balances
AI:  -> calls session_recall("last_person_id")
     -> calls person_leave_status(person_id="abc-123")
     Annual Leave: 8.5 days remaining (out of 14)
     Sick Leave: 10 days remaining
```

#### Requesting Time Off

```
You: I want to take next Monday and Tuesday off as annual leave
AI:  -> calls analyze_leave_impact(person_id="...", requested_days=2)
     You have 8.5 days remaining. After this request: 6.5 days.
     Shall I go ahead and submit this?
You: Yes
AI:  -> calls leave_create(...)
     Leave request submitted for March 16-17.
```

#### Terminating an Employee (with confirmation)

```
You: Terminate Ahmet Kaya effective March 31, reason: voluntary resignation
AI:  -> calls person_terminate(person_id="abc123", termination_date="2026-03-31", reason_code="03")
     [CONFIRM TERMINATION] Permanently terminate Ahmet Kaya on 2026-03-31 (reason code 03)?
     This action cannot be undone.
You: Yes
AI:  Termination recorded. Ahmet Kaya is now inactive.
```

#### Burnout & Wellbeing Check

```
You: How is Ayse doing? Is she at risk of burnout?
AI:  -> calls analyze_employee_wellbeing(person_id="Ayse Yilmaz")
     Red Zone (Score: 5)
     Signals:
     - Unused annual leave > 20 days
     - No rest taken in 94 days (90-day threshold exceeded)

     Bridge Day Opportunities:
     - Take 1 day off around Kurban Bayramı (2026-05-27) -> 7-day break (7.0x efficiency)

     Recommendation: Take Monday-Tuesday before Kurban Bayramı for a full 7-day break
     using only 2 leave credits.
```

#### Smart Rest Planning

```
You: What are the best upcoming rest windows for Mehmet?
AI:  -> calls get_smart_rest_plan(person_id="Mehmet Demir")
     Budget tier: generous (22 days remaining)

     Top 3 rest opportunities:
     1. Take 1 day (Mon 25 May) -> 9-day break (9.0x efficiency)
     2. Take 1 day (Mon 23 Mar) -> 5-day break (5.0x efficiency)
     3. Take 2 days (Mon-Tue 27-28 Apr) -> 5-day break (2.5x efficiency)
```

#### Manager Morning Briefing (using prompt)

```
You: Give me a morning briefing for the Engineering department
AI:  -> uses manager_dashboard prompt
     Engineering Department — Morning Briefing
     - 2 people on leave today (Ayse, Mehmet)
     - 1 pending leave request to approve
     - 3 overtime entries logged yesterday
     - Training "Cloud Security 101" starts next week (4 enrolled)
```

#### Kolay Quiz

```
You: Give me a quiz about my colleagues
AI:  -> calls quiz_challenge(mode="photo_match", count=5)
     I'll show you 5 photos. Can you identify them?

     Question 1: [photo displayed] Who is this person?
     A) Ayse Yilmaz   B) Zeynep Kara   C) Fatma Demir   D) Elif Sahin
You: A
AI:  Correct! That's Ayse Yilmaz from Engineering. 4 more to go!
```

---

## Test with curl

```bash
# discover available tools
curl -X POST https://kolay.up.railway.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

---

## Project Structure

```
src/kolay_cli/
  cli.py              # entry point, global flags
  mcp_server.py       # FastMCP server — tools, prompts, middleware stack
  security.py         # token storage, validation, @require_auth
  server_middleware.py # ASGI token-injection middleware (KolayProxyMiddleware)
  rate_limiter.py     # sliding-window per-token rate limiter
  activity_log.py     # structured JSON activity logging
  api/
    client.py         # HTTP client (requests + retry)
    errors.py         # APIError + exit codes
  commands/           # one module per resource group
    person.py, leave.py, timelog.py, training.py,
    transaction.py, calendar.py, unit.py, approval.py, ...
  mcp/                # MCP tool modules (one file per resource group)
    tools_people.py, tools_leaves.py, tools_time.py,
    tools_training.py, tools_finance.py, tools_org.py,
    tools_analytics.py, tools_wellness.py, tools_misc.py,
    tools_session.py, prompts.py
  services/           # business logic (shared between CLI and MCP)
    hr_analytics.py   # team availability, turnover risk, payroll anomaly detection
    wellness.py       # burnout scoring, bridge-day finder, rest planner
    turkish_holidays.py  # Turkish public holiday calendar (2024-2027 + Google Calendar)
    nudge.py          # contextual reminder hints
    quiz/             # Kolay Quiz game engine
  ui/
    formatters.py     # Rich tables, spinners
    output.py         # JSON mode
    pickers.py        # interactive ID selection
    search.py         # client-side filtering
```

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

## License

MIT
