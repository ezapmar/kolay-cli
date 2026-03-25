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

## [OPENAI CHATGPT CONNECTION]

ChatGPT speaks MCP now. But its Beta connector has no custom header support. We solved it. Your token rides in the URL.

1. Open **chatgpt.com**. Click your profile icon. Go to **Settings**.
2. Find **Connectors** (under Apps). Click **Add** (the "+" button).
3. The **New App** dialog opens. Fill in:
   - **Name:** `Kolay IK`
   - **Description:** `HR management -- employees, leaves, timelogs, trainings, payroll`
   - **MCP Server URL:** `https://kolay.up.railway.app/mcp?token=YOUR_KOLAY_API_TOKEN`
   - **Authentication:** Select **No Auth** from the dropdown.
4. Check **"I understand and want to continue"**.
5. Click **Create**.

That is all. Your AI is now an HR operator.

> If your server also uses a gatekeeper key (`MCP_API_KEY`), append it:
> `https://kolay.up.railway.app/mcp?token=YOUR_TOKEN&api_key=YOUR_MCP_API_KEY`

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

**STOP STRUGGLING.** We refuse to let technical friction slow down your HR workflows. We designed Kolay CLI to be an effortless extension of your mind. If it's not working perfectly, here is exactly how to fix it right now:

- **[UNAUTHORIZED? SHRUNKEN KEYS?]** If your tools suddenly stop returning data, your API token has expired. **RE-ARM IMMEDIATELY** with `kolay auth login`. If you're running headless, let `keyrings.alt` securely manage your file-backed storage!
- **[NEED MORE EYES?]** You hold immense power. Don't guess. Append `--help` (e.g., `kolay person list --help`) to instantly reveal the hidden arsenals of filters, limits, and operational flags!
- **[TALK TO PROTOCOLS?]** Switch to `--json` to obliterate the pretty tables and output razor-sharp, structured JSON. Pipe it directly into `jq` and command your data like a true terminal wizard!
- **[FEELING THE LAG?]** We forged this client for raw speed. If it stutters, check your network or the Kolay status page—we do not compromise on performance!
- **[VIEW THE MAP]** Lost your bearings? Run `kolay config show`. It acts as your absolute compass, instantly exposing your active environment, base URL, and operational settings!
- **[ZERO TRUST, ZERO DRAMA]** Paralyzed by privacy concerns? Read our security documentation. We enforce ruthless PII masking, DLP egress scanners, and military-grade on-device AES-256-GCM encryption by default. 

**You are never alone.** Every error we throw is a tactical guide, never a dead end. If you hit an impenetrable wall, [report it](https://github.com/ezapmar/kolay-cli/issues) and we will tear it down together!

---

## [THE STACK]

- Python 3.10+
- Typer (Interactive CLI)
- FastMCP (Verifiable Smart Proxy)
- AES-256-GCM (AEAD Configuration & Memory Encryption)
- HMAC-SHA256 (PII Masking + Execution Receipts)

---

## [LICENSE]

MIT
