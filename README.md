# kolay-cli

An unofficial AI-powered Command Line Interface and MCP Server for Kolay İK.

```
           ████████████████████
          ████████████████████
         ████              ████
        ████              ████      ██  ██   ████   ██       ████   ██  ██
       ████              ████       ██ ██   ██  ██  ██      ██  ██  ██  ██
      ████              ████        ████    ██  ██  ██      ██████   ████
     ████              ████         ██ ██   ██  ██  ██      ██  ██    ██
      ████            ████          ██  ██   ████   ██████  ██  ██  ███
       ████████████████████                                        ██
        ████████████████████                                     ███
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

## MCP Server Integration

Turn your AI assistant into an HR expert. `kolay-cli` exposes its logic as an MCP server.

### Automated Installation
Inject the MCP configuration into your favorite client:

```bash
kolay mcp install
```

Supported clients: **Claude Desktop**, **Cursor**, **VS Code** (via Claude Dev/Continue).

## Output Modes

| Flag | Description |
|---|---|
| `--json` | Returns machine-readable JSON for prompts or scripts. |
| `--yes` | Bypasses confirmation prompts for destructive actions. |
| `--debug` | Logs HTTP traces to `~/.config/kolay/debug.log`. |

## Notice

This is an unofficial laboratory project. It is not an official product of Kolay Yazılım A.Ş. The authors are not responsible for data loss or system errors. Write operations modify live production data. Use with caution.

Built with ❤️ for the Kolay İK community.
