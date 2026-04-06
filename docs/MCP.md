<!-- =========================================================================
     docs/MCP.md — Kolay MCP Server reference
     =========================================================================
     MAINTENANCE POLICY
     Append new tools to the tool table. Append new clients to the client
     section. Do not rewrite existing sections unless a fact has changed.
     ========================================================================= -->

# Kolay MCP Server

Model Context Protocol server for [Kolay IK](https://kolayik.com).
Connect any MCP-compatible AI assistant to your HR platform.

> **Disclaimer.** This is an independent project, not an official Kolay Yazilim A.S. product.
> All write operations target live HR data. There is no sandbox.
> You are responsible for your API token and all actions performed.

---

## Table of Contents

- [Overview](#overview)
- [Which Setup Do I Need?](#which-setup-do-i-need)
- [Installation](#installation)
  - [Option 1: Public Server (No Deployment)](#option-1-public-server-no-deployment)
  - [Option 2: Local Mode (stdio)](#option-2-local-mode-stdio)
  - [Option 3: Self-Host (Docker / Railway)](#option-3-self-host-docker--railway)
- [Client Setup](#client-setup)
  - [ChatGPT (OpenAI)](#chatgpt-openai)
  - [Claude Desktop (Anthropic)](#claude-desktop-anthropic)
  - [Gemini CLI (Google)](#gemini-cli-google)
  - [Cursor](#cursor)
  - [VS Code (GitHub Copilot)](#vs-code-github-copilot)
  - [Windsurf](#windsurf)
  - [Zed](#zed)
  - [Mistral Le Chat](#mistral-le-chat)
  - [Perplexity AI](#perplexity-ai)
  - [Other Clients](#other-clients)
- [Authentication](#authentication)
- [Available Tools (53)](#available-tools-53)
- [Session Memory](#session-memory)
- [Prompts](#prompts)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Testing with curl](#testing-with-curl)

---

## Overview

`kolay-cli` ships a full [Model Context Protocol](https://modelcontextprotocol.io) server
built on [FastMCP 3.x](https://gofastmcp.com). It exposes **53 tools** covering employee
management, leave requests, timelogs, trainings, payroll, analytics, and wellbeing.

| Mode | Transport | Use case |
|------|-----------|----------|
| Local | stdio | AI clients on your machine (Claude Desktop, Cursor, Gemini CLI) |
| Remote | Streamable HTTP | Web AI clients (ChatGPT, Perplexity, Mistral Le Chat) |

---

## Which Setup Do I Need?

| I want to... | Method | Time |
|--------------|--------|------|
| Use with ChatGPT, Le Chat, Perplexity | [Public Server](#option-1-public-server-no-deployment) | 2 min |
| Use with Claude Desktop, Cursor, Gemini CLI | [Local Mode](#option-2-local-mode-stdio) | 1 min |
| Host my own instance | [Self-Host](#option-3-self-host-docker--railway) | 15 min |

---

## Installation

### Prerequisites

For all options:
- A Kolay IK API token ([app.kolayik.com → Settings → API Tokens](https://app.kolayik.com/settings/developer-settings))

For local mode (Option 2):
- Python 3.10+
- pip, pipx, or uv

For self-hosting (Option 3):
- Docker and Docker Compose, or a Railway account

### Option 1: Public Server (No Deployment)

A shared multi-tenant instance is available at:

```
https://kolay.up.railway.app/mcp
```

Connect using any MCP client with this configuration:

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

Your token is sent per-request over HTTPS. It is never stored on the server.

### Option 2: Local Mode (stdio)

Install the CLI, which includes the MCP server binary:

```bash
# install
pipx install kolay-cli

# authenticate
kolay auth login

# auto-configure all supported AI clients
kolay mcp install
```

The `kolay mcp install` command writes the correct configuration file for each detected
AI client. Restart your AI client after running it.

For manual configuration, add this to your client's MCP config:

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

The `kolay-mcp` binary reads your token from the OS keychain. No credentials appear
in configuration files. No network port is opened.

### Option 3: Self-Host (Docker / Railway)

#### Railway

1. Fork the repository to your GitHub account.
2. Create a Railway project → Deploy from GitHub repo.
3. Set environment variables (see [Security](#security)).
4. Enable public networking. Your endpoint: `https://<your-app>.up.railway.app/mcp`

#### Local Docker

```bash
export KOLAY_API_TOKEN="your-token"
kolay mcp serve --transport http --port 8000
```

#### FastMCP Direct (Development)

If you want to run the server directly using FastMCP:

```bash
# install kolay-cli with all dependencies
pip install kolay-cli

# run in stdio mode (for local AI clients)
kolay-mcp

# run in HTTP mode (for web AI clients)
kolay mcp serve --transport http --port 8000
```

---

## Client Setup

### ChatGPT (OpenAI)

Requires a ChatGPT Plus, Team, or Enterprise subscription.

1. Open [chatgpt.com](https://chatgpt.com) → click your profile → **Settings**.
2. Go to **Apps & Connectors** → **Advanced settings** → toggle **Developer Mode** ON.
3. Click **Create**.
4. Fill in:
   - **Name:** `Kolay IK`
   - **Description:** `HR management — employees, leaves, timelogs, trainings, payroll`
   - **URL:** `https://kolay.up.railway.app/mcp`
5. Add a custom header:
   - **Header name:** `X-Kolay-Token`
   - **Header value:** your Kolay API token
6. Click **Create**.
7. Open a new chat → click **+** → **More** → select **Kolay IK** → ask a question.

After redeploying your server, go to your connector settings and click **Refresh** to reload tools.

### Claude Desktop (Anthropic)

#### Automatic

```bash
kolay mcp install
```

Restart Claude Desktop.

#### Manual (Local stdio)

Open Claude Desktop → **Settings** → **Developer** → **Edit Config**.
Add to `claude_desktop_config.json`:

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

Save and restart Claude Desktop.

Config file locations:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

#### Remote (No local install)

Claude Desktop → **Settings** → **Integrations** → **Add Custom Integration**.
Enter URL: `https://kolay.up.railway.app/mcp`

Claude Desktop supports user elicitation: destructive operations pause and
ask for your explicit confirmation before executing.

### Gemini CLI (Google)

#### Automatic

```bash
kolay mcp install
```

#### Manual

Edit `~/.gemini/settings.json`:

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

For remote mode:

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

### Cursor

#### Automatic

```bash
kolay mcp install
```

#### Manual

Edit `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project):

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

Restart Cursor.

### VS Code (GitHub Copilot)

Open Settings (JSON) and add:

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

### Windsurf

#### Automatic

```bash
kolay mcp install
```

#### Manual

Edit `~/.codeium/windsurf/mcp_config.json`:

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

### Zed

Edit `~/.config/zed/settings.json`:

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

### Mistral Le Chat

1. Open [chat.mistral.ai](https://chat.mistral.ai) → **Intelligence** → **Connectors**.
2. Click **Add Connector** → **Custom MCP Connector**.
3. Fill in:
   - **Name:** `Kolay IK`
   - **URL:** `https://kolay.up.railway.app/mcp`
   - **Authentication:** No Authentication (single-tenant) or HTTP Bearer Token (multi-tenant)
4. Click **Connect**. Toggle Kolay IK on in any chat.

### Perplexity AI

Requires Perplexity Pro.

**macOS app (local MCP):**

1. Open Perplexity → **Settings** → **Connectors**.
2. Install the PerplexityXPC helper if prompted.
3. Click **Add Connector** → **Simple** tab.
4. **Name:** `Kolay IK`, **Command:** `kolay-mcp`
5. Save. Wait for "Running" status.

**Web (remote MCP):**

1. Go to [perplexity.ai](https://www.perplexity.ai) → **Settings** → **Connectors**.
2. Click **+ Custom connector** → **Remote**.
3. Enter URL: `https://kolay.up.railway.app/mcp`, Transport: Streamable HTTP.
4. Save.

### Other Clients

Any MCP-compatible client can connect using:

- **Local:** Run `kolay-mcp` as a subprocess (stdio transport)
- **Remote:** Point to `https://kolay.up.railway.app/mcp` with `X-Kolay-Token` header

---

## Authentication

```
AI Client  →  MCP Handshake (always succeeds)  →  Tool Call  →  Token checked
                                                                   ↓
                                                            Token found → Kolay API
                                                            No token   → Error returned
```

The MCP session always connects. Authentication happens at the tool level.
AI clients can discover tools without authenticating first.

**Token resolution order:**

| Priority | Source | Header |
|----------|--------|--------|
| 1 | Request header | `X-Kolay-Token: <token>` |
| 2 | Authorization header | `Authorization: Bearer <token>` |
| 3 | Environment variable | `KOLAY_API_TOKEN` |

If the token is a JWT, expiration and signature (HS256, if `MCP_JWT_SECRET` is set)
are checked locally with 5 seconds of clock-skew leeway.

---

## Available Tools (53)

### Core HR

| Tool | Description |
|------|-------------|
| `validate_connection` | Check credentials |
| `person_list` | List employees with search and filter |
| `person_view` | Full employee profile |
| `person_summary` | Compact profile summary |
| `person_leave_status` | Leave balances |
| `employee_health_check` | Cross-reference leaves, timelogs, trainings |
| `person_create` | Create employee |
| `person_update` | Update employee fields |
| `person_update_fields` | Update arbitrary fields by raw API name |
| `person_rehire` | Rehire terminated employee |
| `person_terminate` | Terminate employee (requires confirmation) |
| `person_assign_training` | Assign training |
| `person_update_training` | Update training assignment |
| `person_delete_training` | Remove training assignment |
| `leave_list` | List leave requests |
| `leave_view` | View a single leave |
| `analyze_leave_impact` | Dry-run balance check before booking |
| `leave_types` | Available leave types |
| `leave_create` | Submit leave request |
| `leave_cancel` | Cancel leave |
| `timelog_list` | List timelogs |
| `timelog_view` | View timelog |
| `timelog_create` | Create timelog |
| `timelog_delete` | Delete timelog |
| `training_list` | Training catalogue |
| `training_view` | View training |
| `training_create` | Add to catalogue |
| `training_update` | Update training |
| `training_delete` | Delete training (requires confirmation) |
| `person_list_trainings` | Assignments for an employee |
| `person_training_manage` | Assign, update, or remove (unified) |
| `transaction_list` | List transactions |
| `transaction_view` | View transaction |
| `transaction_create` | Create transaction |
| `transaction_delete` | Delete transaction |
| `payroll_sheet_view` | Full payroll sheet |
| `calendar_list` | Calendar events |
| `calendar_view` | View event |
| `calendar_create` | Create event |
| `calendar_update` | Update event |
| `calendar_delete` | Delete event |
| `unit_tree` | Organisational chart |
| `approval_list` | Approval workflows |

### Smart Proxy

| Tool | Description |
|------|-------------|
| `search_employees` | Filtered, projected search (max 50 results) |
| `get_employee_statistics` | Server-side aggregations (headcount, age, tenure) |
| `get_cache_status` | Cache health diagnostic |

### Analytics and Wellbeing

| Tool | Description |
|------|-------------|
| `team_availability_analysis` | Peak absence days and operational risk |
| `turnover_risk_scan` | Burnout and flight risk |
| `payroll_anomaly_detect` | Duplicate/outlier transaction detection |
| `analyze_employee_wellbeing` | Per-employee burnout score and bridge-day finder |
| `get_smart_rest_plan` | Ranked rest windows by leave efficiency |
| `quiz_challenge` | Kolay Quiz challenge |

### Session Memory

| Tool | Description |
|------|-------------|
| `session_remember(key, value)` | Store a named value |
| `session_recall(key)` | Retrieve a stored value |
| `session_forget(key)` | Remove a stored value |

After every `person_view` call, the server automatically stores `last_person_id`,
`last_person_name`, and `last_person_email`.

---

## Prompts

Built-in prompts guide the AI through multi-step workflows:

| Prompt | Purpose |
|--------|---------|
| `employee_snapshot` | Full profile + leave balance report |
| `burnout_analyzer` | Department burnout risk scan |
| `onboarding_plan` | Welcome email, IT checklist, meeting schedule |
| `offboarding_plan` | Leave payout, handover, exit interview |
| `bulk_update_assistant` | Safe bulk data cleanup with confirmation |
| `manager_dashboard` | Morning briefing for a manager |
| `wellbeing_briefing` | Per-employee wellbeing report |
| `hr_trend_analysis` | Company-wide trend report |
| `risk_brief` | Availability and retention risk brief |
| `hr_capabilities` | Feature walkthrough |

---

## Security

Full details: [SECURITY.md](SECURITY.md).

### Public Server

- Stateless. Your token lives in a ContextVar for the duration of one ASGI request.
- No tokens, PII, or HR data are logged or persisted.
- HTTPS (TLS 1.2+) for all traffic. Rate limiting active.

### Local Mode

- Token read from OS keychain. No credentials in config files.
- Communication via stdin/stdout. No network port opened.
- No data leaves your machine.

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `KOLAY_API_TOKEN` | — | Fallback token (single-tenant) |
| `MCP_PII_MASKING_ENABLED` | `false` | Replace names/emails with pseudonyms |
| `MCP_DLP_ENABLED` | `true` | Last-mile TC Kimlik / IBAN redaction |
| `MCP_RATE_LIMIT_ENABLED` | `false` | Per-token rate limiting |
| `MCP_CIRCUIT_BREAKER_ENABLED` | `true` | AI loop protection |
| `MCP_PAYLOAD_PADDING` | `false` | Anti-traffic-analysis padding |
| `MCP_JWT_SECRET` | — | JWT signature verification (HS256) |
| `MCP_RECEIPT_SECRET` | — | HMAC execution receipts |
| `MCP_API_KEY` | — | Gatekeeper key for the public endpoint |
| `KOLAY_SECURITY_PROFILE` | `standard` | `standard` or `enterprise` |

### Tool Annotations

Every tool carries machine-readable safety hints:

- `readOnlyHint` — true if the tool only reads data
- `destructiveHint` — true if the tool can delete or terminate
- `idempotentHint` — true if repeated calls produce the same result
- `openWorldHint` — true if the tool accesses external systems

---

## Troubleshooting

### "validate_connection returns an error"

Your token is missing or invalid. Set it as an environment variable:
```bash
export KOLAY_API_TOKEN="your-token"
```
Or pass it via the `X-Kolay-Token` header in your client config.

### Tools do not appear after connecting

Restart your AI client after adding or modifying MCP configuration.
For ChatGPT, go to your connector settings and click Refresh.

### "kolay-mcp: command not found"

The CLI is not on your PATH. Verify the installation:
```bash
which kolay-mcp
```
If using pipx, ensure `~/.local/bin` is in your PATH.

### Connection timeout on remote server

Check that the server URL is correct and reachable:
```bash
curl -s -o /dev/null -w "%{http_code}" https://kolay.up.railway.app/mcp
```

### Rate limited

If you see rate limit errors, reduce the frequency of tool calls or enable
`MCP_RATE_LIMIT_ENABLED=false` on your self-hosted server.

### Full diagnostic

```bash
kolay doctor
```

---

## Testing with curl

```bash
# discover available tools
curl -X POST https://kolay.up.railway.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

---

## License

MIT
