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

## [THE PLATFORM ARCHITECTURE]

We outgrew the simple pipe. We built an AI-native HR operating system. It operates on three distinct layers. They scale independently. They separate concerns ruthlessly.

### **Layer 1: The Gateway**
Stateless. Relentless. It identifies tenants, throttles abusive loops, meters usage, and protects the core. This is your perimeter.

### **Layer 2: Corporate Memory (Secure RAG)**
Your LLM is generic. Layer 2 makes it specific. It injects your employee handbooks, policies, and knowledge bases directly into the context window. Strict cryptographic namespace isolation guarantees your data never crosses tenant boundaries. Retrieve only. Never train.

### **Layer 3: The Engine (MCP)**
53 high-performance HR tools. They read. They write. They orchestrate complex workflows like turnover risk scanning and anomaly detection. 

---

## [PROPORTIONATE SECURITY]

Security theater is a liability. We analyze actual threat models. We ship two distinct profiles. Set `KOLAY_SECURITY_PROFILE`. Choose your posture.

- **`standard` (Default):** Lean and fast. TLS. Token auth. Rate limiting. Human-in-the-loop for destructive operations. The right choice for 95% of deployments. No unnecessary overhead.
- **`enterprise`:** Absolute compliance. In-memory AES-256-GCM encryption. Egress DLP scanners redacting TC Kimlik and IBANs. Cryptographic HMAC execution receipts. Justified for regulated environments. Overkill for everyone else.

---

## [FOR DEVELOPERS: THE KERNEL]

We broke the monolith. 

Build your own integrations without the CLI bloat. Import the pure kernel.
```bash
pip install kolay-cli
```
```python
from kolay_core import KolayClient, APIError
from kolay_core import services
```

Run the standalone server. Deploy to any network.
```bash
python -m kolay_mcp --transport http
```

---

## [THE GATEWAYS]

Detailed documentation is split for your convenience. Choose your journey:

### [CLI Documentation](docs/CLI.md)
**For the Terminal Wizards.** 
Full command reference, output filters, interactive pickers, and local security. 
> "Everything you need to master your HR data from the shell."

### [MCP Documentation](docs/MCP.md)
**For the AI Architects.** 
Connect ChatGPT, Claude, Gemini, Mistral. Understand the architectural layers. 
> "Turn your LLM into a fully-capable HR operations lead."

### [Security and Privacy](docs/SECURITY.md)
**For the Compliance Officers.** 
Zero-trust architecture, proportioned security profiles, and data sovereignty.
> "How we protect your most sensitive HR data."

---

## [ALPHA DISCLAIMER]

1. **UNOFFICIAL.** Independent lab application. Not a Kolay Yazilim A.S. product.
2. **WRITE OPERATIONS ARE REAL.** This is not a sandbox. Actions modify live HR data.
3. **TOKEN SECURITY.** You are responsible for your API token. Keep it private.

---

## [EMPHATIC UX HELP GUIDE]

**STOP STRUGGLING.** We refuse to let technical friction slow down your HR workflows. We designed Kolay CLI to be an effortless extension of your mind. If it is not working perfectly, fix it right now:

- **[UNAUTHORIZED? SHRUNKEN KEYS?]** If your tools suddenly stop returning data, your API token expired. **RE-ARM IMMEDIATELY** with `kolay auth login`. If you're running headless, let `keyrings.alt` securely manage your file-backed storage.
- **[NEED MORE EYES?]** You hold immense power. Do not guess. Append `--help` (e.g., `kolay person list --help`) to reveal the hidden arsenals of filters and limits.
- **[TALK TO PROTOCOLS?]** Switch to `--json` to obliterate the pretty tables. Output razor-sharp JSON. Pipe it directly into `jq`. Command your data.
- **[FEELING THE LAG?]** We forged this for raw speed. If it stutters, check your network.
- **[ZERO TRUST, ZERO DRAMA]** Paralyzed by privacy concerns? Enable the `enterprise` profile. Rest easy.

**You are never alone.** Every error we throw is a tactical guide, never a dead end. If you hit an impenetrable wall, [report it](https://github.com/ezapmar/kolay-cli/issues). We will tear it down together.

---

## [THE STACK]

- Python 3.10+
- Typer (Interactive CLI)
- FastMCP (Protocol Engine)
- Qdrant & FastEmbed (Vector Memory)
- AES-256-GCM + HMAC-SHA256 (Enterprise Crypto)

---

## [LICENSE]

MIT
