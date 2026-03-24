# Kolay MCP Server Documentation

Model Context Protocol (MCP) server for [Kolay IK](https://kolayik.com). Connect any MCP-compatible AI assistant to your HR platform through natural language.

---

## Table of Contents

- [Overview](#overview)
- [Quick Start -- Which Setup Is Right for Me?](#quick-start----which-setup-is-right-for-me)
- [Installation Methods](#installation-methods)
  - [Option 1: Public Server (Web -- No Deployment)](#option-1-public-server-web----no-deployment)
  - [Option 2: Local Mode (stdio)](#option-2-local-mode-stdio)
  - [Option 3: Self-Host (Railway / Docker)](#option-3-self-host-railway--docker)
- [Client Setup Guides (Detailed)](#client-setup-guides-detailed)
  - [ChatGPT (OpenAI)](#chatgpt-openai)
  - [Claude Desktop (Anthropic)](#claude-desktop-anthropic)
  - [Gemini CLI (Google)](#gemini-cli-google)
  - [Mistral Le Chat](#mistral-le-chat)
  - [Perplexity AI](#perplexity-ai)
  - [Cursor](#cursor)
  - [VS Code (GitHub Copilot)](#vs-code-github-copilot)
  - [Windsurf](#windsurf)
  - [Zed](#zed)
  - [Any Other MCP Client](#any-other-mcp-client)
- [How Authentication Works](#how-authentication-works)
- [Data Security and Encryption](#data-security-and-encryption)
  - [Security Architecture Overview](#security-architecture-overview)
  - [Layer 1: Transport Security (TLS and mTLS)](#layer-1-transport-security-tls-and-mtls)
  - [Layer 2: Authentication and Authorization](#layer-2-authentication-and-authorization)
  - [Layer 3: PII Masking / Pseudonymization](#layer-3-pii-masking--pseudonymization)
  - [Layer 4: Field Sanitizer (Drop-at-the-Door)](#layer-4-field-sanitizer-drop-at-the-door)
  - [Layer 5: Egress DLP Scanner (Last-Mile Redaction)](#layer-5-egress-dlp-scanner-last-mile-redaction)
  - [Layer 6: Encrypted In-Memory Cache](#layer-6-encrypted-in-memory-cache)
  - [Layer 7: Payload Padding (Anti-Traffic Analysis)](#layer-7-payload-padding-anti-traffic-analysis)
  - [Layer 8: Config Encryption at Rest](#layer-8-config-encryption-at-rest)
  - [Layer 9: Rate Limiting](#layer-9-rate-limiting)
  - [Layer 10: AI Circuit Breaker](#layer-10-ai-circuit-breaker)
  - [Layer 11: Activity Logging and Audit Trail](#layer-11-activity-logging-and-audit-trail)
  - [Layer 12: HMAC Execution Receipts](#layer-12-hmac-execution-receipts)
  - [Layer 13: Cryptographic Tenant Isolation](#layer-13-cryptographic-tenant-isolation)
  - [Layer 14: Prompt Injection Guardrails](#layer-14-prompt-injection-guardrails)
  - [Layer 15: Human-in-the-Loop Confirmation](#layer-15-human-in-the-loop-confirmation)
  - [Security Environment Variable Reference](#security-environment-variable-reference)
- [MCP Server Architecture](#mcp-server-architecture)
  - [Middleware Stack](#middleware-stack)
  - [Verifiable Smart Proxy](#verifiable-smart-proxy)
  - [Tool Annotations](#tool-annotations)
- [Available MCP Tools](#available-mcp-tools)
- [Session Memory Tools](#session-memory-tools)
- [MCP Prompts](#mcp-prompts)
- [Usage Examples (AI Conversations)](#usage-examples-ai-conversations)
- [Proxy Monitoring and Limits](#proxy-monitoring-and-limits)
- [Test with curl](#test-with-curl)
- [Verifiable API Manifest](#verifiable-api-manifest)

---

## Overview

`kolay-cli` ships a full [Model Context Protocol](https://modelcontextprotocol.io) server built on [FastMCP 3.x](https://gofastmcp.com). The server exposes **53 tools** covering employee management, leave requests, timelogs, trainings, payroll, analytics, and wellbeing assessments.

The server can run in two modes:

| Mode | Transport | Use case |
|---|---|---|
| **Local** | stdio | AI clients running on your machine (Claude Desktop, Cursor, Gemini CLI) |
| **Remote** | HTTP/SSE (Streamable HTTP) | Web-based AI clients (ChatGPT, Perplexity, Mistral Le Chat) |

---

## Quick Start -- Which Setup Is Right for Me?

| I want to... | Method | Time |
|---|---|---|
| Use with ChatGPT, Le Chat, Perplexity, or any web AI | [Public Server (Option 1)](#option-1-public-server-web----no-deployment) | 2 min |
| Use with Claude Desktop, Cursor, Gemini CLI | [Local Mode (Option 2)](#option-2-local-mode-stdio) | 1 min |
| Full control, own hosting | [Self-Host (Option 3)](#option-3-self-host-railway--docker) | 15 min |

---

## Installation Methods

### Option 1: Public Server (Web -- No Deployment)

A shared multi-tenant endpoint is available at:

```
https://kolay.up.railway.app/mcp
```

Each user sends their own Kolay IK token via the `X-Kolay-Token` header. **No tokens are stored on the server**; they are used only for the duration of each request and discarded immediately.

**Connect from any MCP client:**

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

**Security notes for the public server:**
- The server is entirely **stateless**. Per-request tokens live only in a ContextVar for the duration of the ASGI call.
- No tokens, PII, or HR response data are ever logged or persisted.
- HTTPS (TLS 1.2+) encrypts all traffic in transit.
- Rate limiting is active to prevent abuse.

---

### Option 2: Local Mode (stdio)

For AI clients running on your machine. The MCP server runs as a child process communicating via stdin/stdout JSON-RPC.

**Automatic installation (recommended):**

```bash
# install the CLI first
pipx install kolay-cli

# authenticate
kolay auth login

# install MCP config for all supported clients
kolay mcp install
```

The installer automatically writes the correct config for each supported client:

| Client | Config Location |
|---|---|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Cursor (global) | `~/.cursor/mcp.json` |
| Cursor (project) | `.cursor/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| Gemini CLI | `~/.gemini/settings.json` |
| VS Code (Copilot) | User-level `mcp.json` |
| Zed | `~/.config/zed/settings.json` |

**Always restart your AI client after running `kolay mcp install`.**

**Security notes for local mode:**
- The token is read from your OS keychain (macOS Keychain, GNOME Keyring, or Windows Credential Vault).
- No network exposure -- communication happens via stdin/stdout within your machine.
- No HTTP server is started.

---

### Option 3: Self-Host (Railway / Docker)

Deploy your own private instance for full control over data residency and security.

**Step 1 -- Push to GitHub:**

```bash
git clone https://github.com/ezapmar/kolay-cli.git
cd kolay-cli
git remote set-url origin https://github.com/YOUR-ORG/kolay-cli.git
git push
```

**Step 2 -- Deploy on Railway:**

1. Create a Railway project -> **Deploy from GitHub repo**
2. Set environment variables (see [Security Environment Variable Reference](#security-environment-variable-reference))
3. Enable public networking

**Step 3 -- Your endpoint:**

```
https://<your-app>.up.railway.app/mcp
```

**Step 4 -- Run locally (HTTP mode) for testing:**

```bash
export KOLAY_API_TOKEN="your-token"
kolay mcp serve --transport http --port 8000
```

---

## Client Setup Guides (Detailed)

### ChatGPT (OpenAI)

ChatGPT supports remote MCP servers as **Apps**. Available on all plans. Requires **Developer Mode**.

> ChatGPT connects to remote MCP servers only. Your MCP server must be reachable over HTTPS.

**Step 1 -- Enable Developer Mode:**

1. Open [chatgpt.com](https://chatgpt.com) -> your profile icon -> **Settings**
2. Go to **Apps & Connectors** -> scroll to **Advanced settings**
3. Toggle **Developer mode** ON

**Step 2 -- Create the connector:**

1. In **Settings -> Apps & Connectors**, click **Create**
2. Fill in:
   - **Connector name**: `Kolay IK`
   - **Description**: `HR management -- employees, leaves, timelogs, trainings, payroll`
   - **Connector URL**: `https://kolay.up.railway.app/mcp`
3. Click **Create**

**Step 3 -- Add authentication (multi-tenant):**

If your server requires an `X-Kolay-Token` header:
1. In the connector settings, add a custom header
2. **Header name**: `X-Kolay-Token`
3. **Header value**: Your Kolay API token

**Step 4 -- Use it:**

1. Open a new chat -> click **+** -> **More** -> select **Kolay IK**
2. Ask: `Show me all active employees`

> After redeploying your server, go to **Settings -> Apps & Connectors** -> your connector -> **Refresh** to reload the tool list.

**Security considerations for ChatGPT:**
- Your token is sent as an HTTP header to the MCP server over HTTPS.
- OpenAI does not store MCP server credentials; they are sent per-request.
- Enable `MCP_PII_MASKING_ENABLED=true` on the server to prevent real names from reaching the LLM.

---

### Claude Desktop (Anthropic)

Claude Desktop supports **both local (stdio) and remote MCP servers**.

#### Local Mode (Recommended)

**Automatic:**

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

#### Remote Mode (No Local Install)

1. Claude Desktop -> **Settings** -> **Connectors** -> **Add custom connector**
2. Enter URL: `https://kolay.up.railway.app/mcp`

**Security considerations for Claude:**
- Claude Desktop supports **user elicitation**. Destructive operations (terminate employee, delete training) will pause and ask for your explicit confirmation before executing.
- In local mode, your token never leaves your machine.
- In remote mode, the token is sent via HTTPS headers.

---

### Gemini CLI (Google)

Gemini CLI supports **local (stdio) MCP servers** natively.

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

**For remote mode (SSE/HTTP):** If you want to connect Gemini CLI to a remote server instead:

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

**Security considerations for Gemini CLI:**
- In local mode, the `kolay-mcp` binary reads the token from your OS keychain. No credentials appear in `settings.json`.
- Gemini CLI runs the MCP server as a subprocess; no network port is opened.

---

### Mistral Le Chat

Mistral Le Chat supports **remote MCP servers** via custom connectors.

1. Open [chat.mistral.ai](https://chat.mistral.ai) -> **Intelligence** -> **Connectors**
2. Click **Add Connector** -> **Custom MCP Connector**
3. Fill in:
   - **Name**: `Kolay IK`
   - **URL**: `https://kolay.up.railway.app/mcp`
   - **Authentication**:
     - **No Authentication** (single-tenant: server uses `KOLAY_API_TOKEN` env var)
     - **HTTP Bearer Token** (multi-tenant: Le Chat sends the token as `Authorization: Bearer <token>`)
4. Click **Connect**
5. In any chat, toggle the Kolay IK connector on and ask.

> Le Chat auto-detects available tools. No per-tool configuration needed.

**Security considerations for Mistral:**
- Mistral sends your token using the standard `Authorization: Bearer` header.
- The server middleware extracts this and injects it into the request context.
- Enable `MCP_PII_MASKING_ENABLED=true` to prevent real employee names from reaching Le Chat.

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
5. Open a new thread, enable the **Kolay IK** connector, and ask.

**Security considerations for Perplexity:**
- Same transport-level security as other web clients (HTTPS + per-request tokens).
- Perplexity does not expose an MCP local mode; all traffic goes over the network.

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

**Security considerations for Cursor:**
- Local stdio mode: the server runs as a child process. No network exposure.
- Token is resolved from your OS keychain, not from the config file.

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

**Security considerations for VS Code:**
- Same local stdio model as Cursor. No network port opened.

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

The MCP session **always connects**. Authentication happens at the **tool level** -- every HR tool checks for a valid token before accessing data. AI clients can discover tools without authenticating first.

**Token resolution order (per request):**

| Priority | Source | Header |
|---|---|---|
| 1 | Request header | `X-Kolay-Token: <token>` |
| 2 | Authorization header | `Authorization: Bearer <token>` |
| 3 | Environment variable | `KOLAY_API_TOKEN` (single-tenant fallback) |

**JWT validation:**
- If the token is a JWT, expiration is checked locally with 5 seconds of clock-skew leeway.
- If `MCP_JWT_SECRET` is set, cryptographic signature verification (HS256) is enforced.
- Opaque tokens (non-JWT) are accepted as-is; the Kolay API validates them on each call.

---

### Data Security and Privacy

The Kolay MCP server is built with a **defense-in-depth** security architecture. Because it processes sensitive HR data, we implement 15 independent security layers to ensure privacy, compliance, and protection against abuse.

For the full technical breakdown, including encryption details, PII masking, and DLP configurations, please see the:

### [Security, Privacy, and Encryption Guide](SECURITY.md)

**Key features include:**
- **PII Masking:** Automatic pseudonymization of names and emails before they reach the LLM.
- **Egress DLP Scanner:** Last-mile redaction of TC Kimlik, IBAN, and credit card patterns.
- **Field Sanitizer:** Whitelist-only approach that drops 50+ sensitive fields at the entry point.
- **Encrypted Cache:** In-memory ciphertext storage with ephemeral RAM-only keys.
- **AI Circuit Breaker:** Protection against infinite tool-calling loops.
- **mTLS Support:** Mutual TLS for secure, certificate-based machine-to-machine communication.

### Verifiable Smart Proxy

The server includes a **Verifiable Smart Proxy** layer to protect your LLM context window and API quotas:

- **In-Memory TTL Caching:** API responses are cached for 5 minutes (configurable). Rapid-fire LLM reasoning steps hit the high-speed local cache instead of the Kolay API.
- **Server-Side Projection:** Tools like `search_employees` strip 50+ unneeded columns, sending only the fields the LLM needs.
- **Hard-Limit Truncation:** Large results are capped at 50 records. If data is truncated, a `_meta.warning` hint encourages the LLM to narrow its search.
- **Verifiable API Manifest:** Independent agents can cryptographically verify server identity using the JWS-signed `mcp-manifest.json`.

### Tool Annotations

Every tool carries machine-readable hints for LLM client safety layers:

- `readOnlyHint` -- True if the tool only reads data
- `destructiveHint` -- True if the tool can delete or terminate
- `idempotentHint` -- True if repeated calls produce the same result
- `openWorldHint` -- True if the tool accesses external systems

**Component tags:** Every tool is tagged `read`, `write`, `destructive`, `admin`, `analytics`, or `wellness`. MCP clients that support tag filtering can expose only appropriate tools for the current user's role.

**Tool timeouts:**

| Tool | Timeout |
|---|---|
| `team_availability_analysis` | 90 s |
| `turnover_risk_scan` | 90 s |
| `payroll_anomaly_detect` | 45 s |
| `analyze_employee_wellbeing` | 60 s |
| `get_smart_rest_plan` | 60 s |

---

## Available MCP Tools

The server exposes **53 tools** to AI clients.

### Core HR Tools

| Tool | Tags | Description |
|---|---|---|
| `validate_connection` | read | Check if credentials are working |
| `person_list` | read | List employees with search and filter |
| `person_view` | read | View full employee profile |
| `person_summary` | read | Compact profile summary |
| `person_leave_status` | read | View leave balances |
| `employee_health_check` | read | Cross-reference leaves, timelogs, trainings |
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
| `training_delete` | destructive, admin | Delete training (requires confirmation) |
| `transaction_list` | read | List transactions |
| `transaction_view` | read | View a single transaction |
| `payroll_sheet_view` | read | View the full payroll sheet |
| `transaction_create` | write | Create a transaction |
| `transaction_delete` | destructive | Delete a transaction |
| `calendar_list` | read | List calendar events |
| `calendar_view` | read | View a single event |
| `unit_tree` | read | View the organisational chart |
| `approval_list` | read | List approval workflows |
| `calendar_create` | write | Create a calendar event |
| `calendar_update` | write | Update a calendar event |
| `calendar_delete` | destructive | Delete a calendar event |

### Smart Proxy Tools

| Tool | Tags | Description |
|---|---|---|
| `search_employees` | read, smart_proxy | Filtered, projected employee search (hard-capped at 50) |
| `get_employee_statistics` | read, smart_proxy, analytics | Server-side aggregations (headcount, age, tenure) |
| `get_cache_status` | read, smart_proxy, diagnostic | Check TTL cache health |

### Analytics and Wellbeing Engine

| Tool | Tags | Description |
|---|---|---|
| `team_availability_analysis` | read, analytics | Peak absence days + operational risk |
| `turnover_risk_scan` | read, analytics | Burnout and flight risk scan |
| `payroll_anomaly_detect` | read, analytics | Duplicate/outlier transaction detection |
| `analyze_employee_wellbeing` | read, wellness | Per-employee burnout score + bridge-day finder |
| `get_smart_rest_plan` | read, wellness | Ranked rest windows by leave efficiency |
| `quiz_challenge` | read | Generate a Kolay Quiz challenge |

---

## Session Memory Tools

Three tools give the AI explicit, LLM-controlled memory across tool calls. No data is written to disk. Memory clears when the session ends.

| Tool | Description |
|---|---|
| `session_remember(key, value)` | Store a named value |
| `session_recall(key)` | Retrieve a stored value |
| `session_forget(key)` | Remove a stored value |

**Auto-caching:** After every `person_view` call, the server automatically stores `last_person_id`, `last_person_name`, and `last_person_email` in session state.

---

## MCP Prompts

Built-in prompts guide the AI through complex multi-step workflows:

| Prompt | What it does |
|---|---|
| `employee_snapshot` | Full profile + leave balance report |
| `burnout_analyzer` | Scan a department for burnout risk |
| `onboarding_plan` | Welcome email, IT checklist, meeting schedule |
| `offboarding_plan` | Leave payout, handover checklist, exit interview |
| `bulk_update_assistant` | Safe bulk data cleanup with human confirmation |
| `manager_dashboard` | Morning briefing for a department manager |
| `wellbeing_briefing` | Per-employee wellbeing report |
| `hr_trend_analysis` | Company-wide trend report |
| `risk_brief` | Availability and retention risk brief |
| `hr_capabilities` | Guided prompt explaining all features |

---

## Usage Examples (AI Conversations)

**Listing employees:**

```
You: Show me all active employees
AI:  -> calls person_list(status="active", limit=20)
     Found 47 employees. Here are the first 20:
     1. Ayse Yilmaz -- Engineering
     2. Mehmet Demir -- Marketing
     ...
```

**Requesting time off:**

```
You: I want to take next Monday and Tuesday off as annual leave
AI:  -> calls analyze_leave_impact(person_id="...", requested_days=2)
     You have 8.5 days remaining. After this request: 6.5 days.
     Shall I go ahead and submit this?
You: Yes
AI:  -> calls leave_create(...)
     Leave request submitted for March 16-17.
```

**Burnout check:**

```
You: How is Ayse doing? Is she at risk of burnout?
AI:  -> calls analyze_employee_wellbeing(person_id="Ayse Yilmaz")
     Red Zone (Score: 5)
     Signals:
     - Unused annual leave > 20 days
     - No rest taken in 94 days

     Bridge Day Opportunities:
     - Take 1 day off around Kurban Bayrami -> 7-day break (7.0x efficiency)
```

**Termination with confirmation:**

```
You: Terminate Ahmet Kaya effective March 31, reason: voluntary resignation
AI:  -> calls person_terminate(...)
     [CONFIRM TERMINATION] Permanently terminate Ahmet Kaya on 2026-03-31?
     This action cannot be undone.
You: Yes
AI:  Termination recorded. Ahmet Kaya is now inactive.
```

---

## Proxy Monitoring and Limits

**Activity logging:** Always active. Structured JSON logs for every tool invocation to `stdout`.

**Rate limiting:** Opt-in via `MCP_RATE_LIMIT_ENABLED=true`. Tracked by privacy-safe token hash.

**Response size guard:** Tool responses exceeding 500 KB are automatically truncated.

---

## Test with curl

```bash
# discover available tools
curl -X POST https://kolay.up.railway.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

---

## Verifiable API Manifest

The server includes a JWS-signed `mcp-manifest.json` that independent agents can use to cryptographically verify the server's identity and capabilities:

```json
{
  "schema_version": "1.0",
  "server": {
    "name": "kolay-ik",
    "display_name": "Kolay IK MCP Server",
    "version": "0.13.0-alpha"
  },
  "data_policies": {
    "no_llm_training": true,
    "pii_masking_available": true,
    "max_response_size_bytes": 500000,
    "rate_limiting": "sliding_window_per_token",
    "audit_logging": "structured_json_stdout",
    "data_retention": "none_stateless_proxy"
  }
}
```

- `no_llm_training: true` -- The server declares that no HR data should be used for LLM training.
- `data_retention: none_stateless_proxy` -- No HR data is persisted beyond the in-memory cache TTL.

---

## License

MIT
