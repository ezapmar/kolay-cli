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
