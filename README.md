# Disclaimer and Legal Notice (Alpha Release)

1. **Unofficial Lab Application:** This project is an independent "lab/R&D" application. It is not an official product or service of Kolay İK. **Kolay Yazılım A.Ş.** cannot be held responsible for any data loss, system errors, or damages arising from the use of this software.
2. **Token and Data Security:** The creation and secure storage of API tokens are entirely the user's responsibility. Please follow Kolay İK's official instructions and security guidelines when generating tokens to prevent unauthorized access.
3. **Operational Risks:** Please use the tools and operations performed via the MCP and CLI carefully. Write/update actions and bulk operations can cause permanent changes or damage to your live HR data. 
4. **Early Development Stage (Alpha):** This application is currently in its **Alpha** stage and is under active development. It may contain unexpected bugs. You can submit any bug reports, feedback, or feature requests via the GitHub [Issues](https://github.com/ezapmar/kolay-cli/issues) page.

---

# kolay-cli

An unofficial AI-powered Command Line Interface and MCP Server for Kolay İK.

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

**kolay-cli** allows you to manage your HR tasks, employee records, and company workflows directly from your terminal. It provides lightweight access to the Kolay İK API and serves as a local [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for AI assistants like Claude and Cursor.

## Key Features

*   **Natural Language HR**: Use the built-in MCP server to talk to your HR data using AI.
*   **Complete Resource Management**: Manage People, Leaves, Timelogs, Trainings, and Finance.
*   **Secure by Design**: API tokens are stored in your OS Keychain (macOS, Windows, Linux).
*   **CLI First UX**: Interactive ID pickers, human-readable tables, and guided setup.
*   **Developer Friendly**: Full JSON output mode for automation and scripting.
*   **Health Diagnostics**: Built-in `doctor` command to verify connectivity and credentials.

## Installation

Install via `pipx` (recommended) to keep dependencies isolated:

```bash
pipx install kolay-cli
```

Or via `pip`:

```bash
pip install kolay-cli
```

## Quickstart

### 1. Authenticate
Configure your session by providing your Kolay API token. You can generate a token at [app.kolayik.com/settings/developer-settings](https://app.kolayik.com/settings/developer-settings).

```bash
kolay auth login
```

### 2. Verify Health
Ensure your connection is healthy and authorized.

```bash
kolay doctor
```

### 3. Start Managing
List your colleagues or create a leave request.

```bash
# List top 10 employees
kolay person list --limit 10

# Create an annual leave request
kolay leave create --type annual --start 2026-03-01 --end 2026-03-03
```

### 4. Enhance Productivity with Behavioral Nudges

**kolay-cli** includes an intelligent Behavioral Nudge Engine functioning as your personal productivity coach. Instead of overwhelming you with a massive backlog, it distills your tasks into actionable, time-boxed bursts.

Configure your personalized interaction style:

```bash
kolay nudge configure
```

You can choose your cadence (daily, weekly), preferred style (gentle, direct, gamification), and your sprint lengths.

Ready to crush some tasks? Start a focused micro-sprint:

```bash
kolay nudge sprint
```

*The Coach says: "You have 5 pending items in other areas. Clear them in 5 mins with `kolay nudge sprint`!"*

## MCP Server Integration

Turn your AI assistant into an HR expert. `kolay-cli` exposes its full functionality as an MCP server.

### Local Clients (stdio)

For clients running on your machine, use the automated installer:

```bash
kolay mcp install
```

This writes the configuration into the correct file for each client. Supported local clients:

| Client | Config Path |
|---|---|
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Cursor** (global) | `~/.cursor/mcp.json` |
| **Cursor** (project) | `.cursor/mcp.json` in your working directory |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` |
| **Gemini CLI** | `~/.gemini/settings.json` |
| **VS Code** (Copilot) | User-level `mcp.json` |
| **Zed** | `~/.config/zed/settings.json` |

Restart your client after running `kolay mcp install` to activate the connection.

### Mistral Le Chat (remote)

[Le Chat](https://chat.mistral.ai) supports MCP through remote HTTP connectors. To connect kolay-cli:

**1. Start the MCP server in HTTP mode:**

```bash
kolay mcp serve --transport http --port 8000
```

This starts the server at `http://localhost:8000/mcp`. If you want to expose it to the internet (for Le Chat cloud access), deploy it on a server with a public IP or use a tunnel like [ngrok](https://ngrok.com):

```bash
ngrok http 8000
```

**2. Add the connector in Le Chat:**

1. Go to [chat.mistral.ai/connections](https://chat.mistral.ai/connections)
2. Click **Add custom connector**
3. Enter your MCP server URL (e.g. `https://your-ngrok-url.ngrok.io/mcp`)
4. Save and start chatting with your HR data

> **Note:** The HTTP endpoint does not include authentication by default. When exposing your MCP server to the internet, use a reverse proxy with HTTPS and token-based access control.

## Output Modes

| Flag | Description |
|---|---|
| `--json` | Returns machine-readable JSON for prompts or scripts. |
| `--yes` | Bypasses confirmation prompts for destructive actions. |
| `--debug` | Logs HTTP traces to `~/.config/kolay/debug.log`. |
