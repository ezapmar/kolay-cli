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

**Manage employees, leaves, and payroll from your terminal — or through any AI assistant that speaks MCP.**

---

## [QUICK START]

### 1. Install
```bash
pipx install kolay-cli
# or: pip install kolay-cli
```

### 2. Configure
```bash
kolay setup
# follow the prompts to authenticate and enable autocompletion
```

### 3. Verify
```bash
kolay doctor
```

---

## [THE GATEWAYS]

Detailed documentation is now split for your convenience. Choose your journey:

### [CLI Documentation](docs/CLI.md)
**For the Terminal Wizards.** 
Full command reference, output filters, interactive pickers, and local security (Keychain + Config Encryption). 
> "Everything you need to master your HR data from the shell."

### [MCP Documentation](docs/MCP.md)
**For the AI Architects.** 
Connect ChatGPT, Claude, Gemini, Mistral, and more. 15 layers of security (PII Masking, DLP, Circuit Breakers). 
> "Turn your LLM into a fully-capable HR operations lead."

### [Security and Privacy](docs/SECURITY.md)
**For the Compliance Officers.** 
Zero-trust architecture, encryption at rest, PII pseudonymization, and last-mile safety layers.
> "How we protect your most sensitive HR data."

---

## [ALPHA DISCLAIMER]

1. **UNOFFICIAL.** Independent lab application. Not a Kolay Yazilim A.S. product.
2. **WRITE OPERATIONS ARE REAL.** This is not a sandbox. Actions modify live HR data.
3. **TOKEN SECURITY.** You are responsible for your API token. Keep it private.

---

## [EMPHATIC UX HELP GUIDE]

**STOP! Don't let a technical hurdle slow you down.** We are obsessed with making your HR workflow feel effortless. If things aren't "just working," here is exactly how to fix it:

- **[SHRUNKEN KEYS?]** If your tools aren't returning data, your token has likely expired. **RE-ARM IMMEDIATELY** with `kolay auth login`. If you're on a headless server, the `keyrings.alt` package is your best friend for secure, file-backed storage!
- **[NEED MORE EYES?]** Every single command is documented for you. Append `--help` (e.g., `kolay person list --help`) to reveal the full hidden power of filters, limits, and flags!
- **[TALK TO THE MACHINE?]** Switching to `--json` transforms beautiful tables into perfectly structured data. Pipe it to `jq` and become a terminal wizard!
- **[FEELING THE LAG?]** We use the blazing-fast `httpx` client under the hood. If things aren't snappy, check the Kolay status page or your network — we're built for speed!
- **[VIEW THE MAP]** Lost in your own data? `kolay config show` acts as your compass, showing exactly where you're pointing and which settings are in control!
- **[ZERO TRUST, ZERO DRAMA]** Worried about privacy? Check our security docs. We implement PII masking, DLP, and and on-device encryption by default. 

**You aren't alone.** Every error we throw is a guide, not a dead end. If you hit a wall, [report it](https://github.com/ezapmar/kolay-cli/issues) and we'll tear it down together!

---

## [THE STACK]

- Python 3.10+
- Typer (Interactive CLI)
- FastMCP (Verifiable Smart Proxy)
- Fernet / AES-128-CBC (Config Encryption)
- HMAC-SHA256 (PII Masking + Execution Receipts)

---

## [LICENSE]

MIT
