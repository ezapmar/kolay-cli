<!-- =========================================================================
     README.md — Canonical project overview for kolay-cli
     =========================================================================
     MAINTENANCE POLICY
     This file is the single source of truth for the project's public face.
     Do NOT rewrite, restructure, or rephrase existing sections during routine
     code changes. If a new feature is added, append a line to the relevant
     section. If a section becomes factually wrong, correct the fact only.
     Full rewrites require explicit human approval.
     ========================================================================= -->

# Kolay CLI and MCP Server

> **Disclaimer.** This is an independent, community-maintained project.
> It is **not** an official product of Kolay Yazilim A.S. and carries no
> endorsement, warranty, or support from the company. All write operations
> target live HR data — there is no sandbox. You are solely responsible for
> your API token and the actions performed through this software.

Command-line interface and AI integration server for [Kolay IK](https://kolayik.com).
Manage employees, leaves, timelogs, trainings, payroll, and organizational
structure from the terminal or through any AI assistant that speaks
[Model Context Protocol](https://modelcontextprotocol.io).

---

## Quick Start

```bash
# 1. Install
pipx install kolay-cli          # or: pip install kolay-cli

# 2. Authenticate
kolay setup                     # guided first-time setup

# 3. Verify
kolay doctor                    # health check
```

Requires Python 3.10 or later.

---

## What This Package Provides

| Binary | Purpose |
|--------|---------|
| `kolay` | Interactive CLI for terminal use |
| `kolay-mcp` | MCP server binary for AI clients |

The same `pip install kolay-cli` command installs both.

---

## Documentation

Detailed guides are maintained separately for each component:

| Guide | Audience | Contents |
|-------|----------|----------|
| [docs/CLI.md](docs/CLI.md) | Terminal users, scripts, CI pipelines | Full command reference, output modes, shell completion, local security |
| [docs/MCP.md](docs/MCP.md) | AI integrators, platform teams | Client setup (ChatGPT, Claude, Gemini, Cursor, etc.), tool catalogue, architecture |
| [docs/BOX.md](docs/BOX.md) | Self-hosting teams, IT administrators | Docker Compose deployment, GPU/CPU modes, troubleshooting |
| [docs/SECURITY.md](docs/SECURITY.md) | Security reviewers, compliance officers | Encryption, PII masking, DLP, rate limiting, audit trail |

---

## Connecting AI Assistants

### ChatGPT

1. Open [chatgpt.com](https://chatgpt.com) → Settings → Apps & Connectors.
2. Enable Developer Mode under Advanced settings.
3. Click Create. Enter:
   - **Name:** `Kolay IK`
   - **URL:** `https://kolay.up.railway.app/mcp`
4. Add a custom header: `X-Kolay-Token` → your Kolay API token.
5. Save. Open a new chat, attach the Kolay IK app, and ask.

### Claude Desktop

```bash
kolay mcp install       # writes claude_desktop_config.json automatically
```

Or manually add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

### Other Clients

Local (stdio): run `kolay-mcp` as a subprocess.
Remote (HTTP): point to `https://kolay.up.railway.app/mcp` with an `X-Kolay-Token` header.

See [docs/MCP.md](docs/MCP.md) for Gemini CLI, Cursor, VS Code, Windsurf, Zed, Mistral, and Perplexity instructions.

---

## Self-Hosted AI (Kolay AI Box)

Run a fully private AI HR assistant on your own hardware. No cloud dependency.

```bash
cd box
make dev          # CPU mode (Mac, laptop)
# or
make up           # GPU mode (NVIDIA)
```

Open `http://localhost:3000`. See [docs/BOX.md](docs/BOX.md) for full setup instructions.

---

## Security Overview

| Layer | What it protects |
|-------|------------------|
| OS keychain | API token at rest (macOS Keychain, GNOME Keyring, Windows Vault) |
| AES-256-GCM | Local config file encryption (opt-in) |
| TLS 1.2+ | All network traffic |
| PII masking | Names and emails replaced with pseudonyms before reaching the LLM |
| Egress DLP | Last-mile redaction of TC Kimlik and IBAN patterns |
| Rate limiter | Per-token sliding window to prevent abuse |
| Circuit breaker | Stops infinite AI tool-calling loops |
| Audit log | Local append-only log of all write operations, with 5 MB rotation |

Two profiles are available via `KOLAY_SECURITY_PROFILE`:

- **`standard`** (default): TLS, token auth, rate limiting, human-in-the-loop for destructive ops.
- **`enterprise`**: Adds AES-256-GCM encryption, DLP scanning, HMAC execution receipts.

Full details: [docs/SECURITY.md](docs/SECURITY.md).

---

## Development

```bash
# install with test dependencies
pip install -e ".[test,dev]"

# run tests
uv run --extra test pytest tests/ -v
```

---

## Stack

- Python 3.10+
- Typer + Rich (CLI)
- FastMCP 3.x (MCP protocol engine)
- AES-256-GCM + PBKDF2 (local encryption)
- Qdrant + FastEmbed (RAG, optional)

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General / server error |
| 2 | Bad input / validation |
| 3 | Not found |
| 4 | Auth / permission denied |
| 5 | Conflict |

---

## License

MIT
