# Kolay AI Box — Master Implementation Plan

**Version:** 2.0 — April 2026
**Status:** Ready to Execute
**Repo:** `kolay-cli` (this repo) — Box lives in `box/` subdirectory

---

## 1. Vision

```
User gets a Kolay IK API token
      │
      ▼
User opens our URL → enters token → chat opens
      │
      ▼
Gemma 4 runs on our server (Ollama)
      │
      ▼
User asks questions → AI fetches data from Kolay IK via MCP tools
      │
      ▼
AI answers in natural language + visualizes with charts and diagrams
```

**Feasibility verdict:** Core flow is 95% covered by existing infrastructure.
Visualization is fully achievable via prompt engineering alone — zero new packages to install on the server.

---

## 2. Component Separation (Critical Design Principle)

Each of the three components works **independently**. They share the same underlying Kolay IK API client but have no hard runtime dependencies on each other.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         kolay-cli (this repo)                        │
│                                                                      │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────────┐   │
│  │   CLI           │  │   MCP Server     │  │   AI Box          │   │
│  │   (Typer)       │  │   (FastMCP)      │  │   (Docker stack)  │   │
│  │                 │  │                  │  │                   │   │
│  │  kolay auth     │  │  kolay-mcp       │  │  box/             │   │
│  │  kolay person   │  │  (stdio or HTTP) │  │  docker-compose   │   │
│  │  kolay leave    │  │                  │  │  + Ollama         │   │
│  │  ...            │  │  Deployed on     │  │  + Open WebUI     │   │
│  │                 │  │  Railway today   │  │  + mcpo           │   │
│  │  pip install    │  │  Works with:     │  │                   │   │
│  │  kolay-cli      │  │  Claude, ChatGPT │  │  Installs         │   │
│  │                 │  │  Cursor, Gemini  │  │  kolay-cli        │   │
│  │  STANDALONE     │  │  Any MCP client  │  │  from PyPI        │   │
│  └────────┬────────┘  └────────┬─────────┘  └────────┬──────────┘   │
│           │                    │                      │              │
│           └────────────────────┴──────────────────────┘              │
│                                │                                     │
│                    ┌───────────▼────────────┐                        │
│                    │     Shared Core        │                        │
│                    │  src/kolay_cli/        │                        │
│                    │  ├── api/client.py     │                        │
│                    │  ├── api/errors.py     │                        │
│                    │  └── commands/         │                        │
│                    └───────────┬────────────┘                        │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     Kolay IK REST API    │
                    │     (external)           │
                    └─────────────────────────┘
```

### Independence rules

| Component | Can run without the others? | How |
|-----------|----------------------------|-----|
| **CLI** | Yes | `pip install kolay-cli` + API token |
| **MCP Server** | Yes | `kolay-mcp` via stdio or Railway HTTP endpoint |
| **AI Box** | Yes | Installs `kolay-cli` from PyPI inside Docker image |

The Box does **not** mount or import from the local repo. It uses the published PyPI package.
For local development, `Dockerfile.mcp` can be overridden to install from a local source.

---

## 3. Full System Architecture

### Docker Stack (3 containers)

```
┌──────────────────────────────────────────────────────────────────────┐
│                          KOLAY AI BOX                                │
│                                                                      │
│  ┌───────────────┐    ┌───────────────┐    ┌──────────────────────┐  │
│  │  Open WebUI   │───▶│     mcpo      │───▶│     Kolay MCP        │  │
│  │  (port 3000)  │    │  (port 8000)  │    │     (stdio)          │  │
│  │               │    │               │    │                      │  │
│  │  Chat UI      │    │  MCP→OpenAPI  │    │  kolay-mcp binary    │  │
│  │  Auth         │    │  bridge       │    │  installed from PyPI │  │
│  │  Model mgmt   │    │  Auth inject  │    │  53 HR tools         │  │
│  └──────┬────────┘    └───────────────┘    └──────────┬───────────┘  │
│         │                                             │              │
│  ┌──────▼────────┐                         ┌──────────▼───────────┐  │
│  │   Ollama      │                         │   Kolay IK REST API  │  │
│  │  (port 11434) │                         │   (external)         │  │
│  │  Gemma 4 26B  │                         │   Auth via Bearer    │  │
│  │  (default)    │                         │   token from OWUI    │  │
│  └───────────────┘                         └──────────────────────┘  │
│                                                                      │
│  Persistent Volume (/mnt/kolay-box)                                  │
│  ├── ollama/   ← model weights (~17GB, survives droplet destroy)     │
│  └── webui/    ← users, chats, artifacts, tool configs               │
└──────────────────────────────────────────────────────────────────────┘
```

### Why mcpo (not direct MCP connection)

| Criterion | mcpo | Direct HTTP MCP |
|-----------|------|-----------------|
| Stability | stdio = 867 tests, battle-proven | HTTP mode less tested |
| OWUI compat | mcpo is by the OWUI team | Native MCP in OWUI is newer |
| Auth inject | Clean header passthrough | Manual per-user config |
| Debug | Clear boundary: OWUI → mcpo → MCP | Mixed failure modes |
| **Verdict** | **Use mcpo** | Future option via `docker-compose.direct.yml` |

### Token Flow

```
1. Admin gets API token from Kolay IK (Owner/Manager role required)
         │
2. Admin opens Open WebUI → Admin Settings → External Tools
   Adds tool:  Type: OpenAPI
               URL:  http://mcpo:8000
               Auth: Bearer <KOLAY_API_TOKEN>
         │
3. HR manager types: "Who has the most unused leave in Engineering?"
         │
4. Open WebUI → Ollama/Gemma 4 → decides to call leave_list + person_list
         │
5. Open WebUI → mcpo (injects Bearer token) → kolay-mcp (stdio)
         │
6. kolay-mcp → Kolay IK REST API (authenticated)
         │
7. Response → mcpo → Open WebUI → Gemma 4 → natural language answer + chart
```

**Per-user tokens:** Each HR manager can enter their own token in OWUI External Tools.
The admin does not need to share a global token. Different permission levels are preserved.

---

## 4. Visualization Layer

Zero new packages installed on the server. Both libraries are CDN-loaded by the LLM-generated HTML.

### Tier 0: Mermaid.js — Diagrams (native, no setup)

- **License:** MIT — unrestricted commercial use, SaaS, OEM, white-label
- **Integration:** Open WebUI renders ` ```mermaid ` blocks natively. No Artifacts needed.
- **LLM reliability:** Highest of any library. Simple text syntax, Gemma 4 makes very few errors.
- **HR use cases:** Org charts, approval flows, onboarding timelines, Gantt views, process maps

```
User: "Draw the leave approval workflow"
→ Gemma 4 emits a ```mermaid flowchart block
→ Open WebUI renders it inline. No JS, no CDN call, no iframe.
```

### Tier 1: Chart.js — Data Charts (via Artifacts)

- **License:** MIT — unrestricted commercial use, SaaS, OEM, white-label
- **Integration:** LLM generates a self-contained HTML artifact. Open WebUI renders it in an iframe.
- **LLM reliability:** Highest among chart libraries. Simple declarative API, minimal config surface.
- **HR use cases:** Bar, line, pie, doughnut, radar — headcount, leave trends, overtime, compensation
- **Bundle size:** ~60KB gzipped. CDN-loaded. Nothing installed on server.

```
User: "Show leave usage by department as a pie chart"
→ Gemma 4 calls leave_list + person_list tools
→ Aggregates data
→ Emits a complete HTML artifact:
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
→ Open WebUI Artifacts renders it inline, interactively.
```

### Library Decision Table

| Library | License | LLM Reliability | OWUI Support | Decision |
|---------|---------|-----------------|--------------|----------|
| **Mermaid.js** | MIT | Highest | Native render | **IN — diagrams** |
| **Chart.js** | MIT | Highest | Artifacts | **IN — data charts** |
| Apache ECharts | Apache 2.0 | Medium | Artifacts | Future — heatmap, treemap |
| Plotly.js | MIT | Medium | Artifacts | Future — statistical plots |
| D3.js | ISC | Low | Artifacts | Skip — too complex for LLM codegen |
| Highcharts | Commercial ($366/dev/yr) | High | Artifacts | Skip — Chart.js covers PoC needs |

**Total visualization cost: $0.** No server-side installation. No package management.

---

## 5. Persistent Storage Strategy

Destroy-on-done workflow requires both Docker volumes to survive droplet destruction.
Both are bind-mounted to a DigitalOcean Block Storage Volume that persists independently.

```
docker-compose.yml volumes:
  ollama_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/kolay-box/ollama    ← Block Storage Volume

  webui_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/kolay-box/webui     ← Block Storage Volume
```

### What survives droplet destruction

| Data | Survives? | Location |
|------|-----------|----------|
| Gemma 4 26B model weights (~17GB) | Yes | `ollama_data` on Volume |
| User accounts + passwords | Yes | `webui_data` on Volume |
| All chat history + conversations | Yes | `webui_data` on Volume |
| Chart.js artifacts (generated charts) | Yes | `webui_data` on Volume |
| Mermaid diagrams (in chat) | Yes | `webui_data` on Volume |
| Kolay MCP tool config + Bearer token | Yes | `webui_data` on Volume |
| System prompt configuration | Yes | `webui_data` on Volume |
| **Droplet IP address** | **No** | Re-assign or use Reserved IP |

**Volume sizing:** 20GB ($2/month) covers model weights (~17GB) + OWUI data (~1-2GB with buffer.

---

## 6. Cloud Infrastructure

### DigitalOcean GPU Droplets

| GPU | VRAM | vCPU | RAM | Price | Gemma 4 26B Q4? |
|-----|------|------|-----|-------|-----------------|
| **RTX 4000 Ada** | 20 GB | 8 | 32 GB | **$0.76/hr** | Yes (17GB Q4, fits) |
| L40S | 48 GB | — | — | $1.57/hr | Yes, room to spare |
| H100 | 80 GB | 20 | 240 GB | $3.39/hr | Overkill for PoC |

**Billing rule: powered-off droplets are still billed. Must DESTROY to stop charges.**

### AWS EC2 GPU Instances

| Instance | GPU | VRAM | vCPU | RAM | Price (us-east-1) | Gemma 4 26B Q4? |
|----------|-----|------|------|-----|--------------------|-----------------|
| **g6.xlarge** | 1x L4 | 24 GB | 4 | 16 GB | **$0.80/hr** | Yes |
| g6.2xlarge | 1x L4 | 24 GB | 8 | 32 GB | $0.98/hr | Yes, more CPU |
| g5.xlarge | 1x A10G | 24 GB | 4 | 16 GB | $1.00/hr | Yes |
| g5.2xlarge | 1x A10G | 24 GB | 8 | 32 GB | $1.21/hr | Yes, more CPU |

**Spot instances available at 30–70% discount. Savings Plans: 25–45% off for committed use.**

### Monthly Cost Scenarios

| Scenario | Provider + Instance | Hours/mo | GPU Cost | Volume | Total |
|----------|---------------------|----------|----------|--------|-------|
| **PoC (10 hr/week)** | **DO RTX 4000 Ada** | 40 | $30 | $2 | **~$32/mo** |
| PoC (10 hr/week) | AWS g6.xlarge | 40 | $32 | $2 | ~$34/mo |
| Active pilot (40 hr/week) | DO RTX 4000 Ada | 160 | $122 | $2 | ~$124/mo |
| Active pilot (40 hr/week) | AWS g6.2xlarge | 160 | $157 | $2 | ~$159/mo |
| Always-on (24/7) | DO RTX 4000 Ada | 730 | $555 | $2 | ~$557/mo |
| Always-on (24/7) | AWS g6.2xlarge | 730 | $715 | $2 | ~$717/mo |
| Always-on (24/7, Spot) | AWS g6.2xlarge Spot | 730 | $215–500 | $2 | ~$217–502/mo |

> **PoC choice: DigitalOcean RTX 4000 Ada at $0.76/hr.**
> Create → use → destroy. Only pay for hours used + $2/mo volume. ~$32/month for 10hr/week.

> **Production choice: AWS g6.xlarge with Spot or Savings Plan.**
> More savings options for committed use. Better ecosystem for production (RDS, CloudWatch, IAM).

### DO Billing Gotcha: IP Address

Each new droplet gets a new IP. Options:
- **PoC:** use the raw IP directly — fine for internal use
- **Pilot:** DigitalOcean Reserved IP (~$4/mo) — same IP re-attached to each new droplet

---

## 7. File Structure

```
box/                               ← Independent from CLI and MCP
├── docker-compose.yml             # Production stack
├── docker-compose.dev.yml         # CPU-only override for local dev (no GPU)
├── Dockerfile.mcp                 # Installs kolay-cli from PyPI + mcpo
├── mcpo.config.json               # Points mcpo → kolay-mcp stdio
├── .env.example                   # Copy → .env, fill in token + model
├── prompts/
│   └── system.md                  # HR persona + visualization rules
├── scripts/
│   ├── deploy.sh                  # Create DO droplet, attach volume, docker up
│   ├── teardown.sh                # docker down, detach volume, destroy droplet
│   └── doctor.sh                  # Health check: all services up? model pulled?
└── README.md                      # Deploy in 5 minutes. Under 80 lines.
```

**Total new code: zero Python lines.** Pure Docker config + shell scripts + prompt engineering.

---

## 8. Proposed Changes (File by File)

### [NEW] docker-compose.yml

```yaml
# Production stack — requires NVIDIA GPU passthrough
services:

  ollama:
    image: ollama/ollama:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - ollama_data:/root/.ollama
    entrypoint: >
      sh -c "ollama serve &
             sleep 5 &&
             ollama pull ${OLLAMA_MODEL:-gemma4:26b} &&
             wait"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5

  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "${WEBUI_PORT:-3000}:8080"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
    volumes:
      - webui_data:/app/backend/data
    depends_on:
      ollama:
        condition: service_healthy

  mcpo:
    build:
      context: .
      dockerfile: Dockerfile.mcp
    ports:
      - "8000:8000"           # internal only — not exposed to internet
    environment:
      - KOLAY_API_TOKEN=${KOLAY_API_TOKEN}
      - KOLAY_SECURITY_PROFILE=${KOLAY_SECURITY_PROFILE:-standard}

volumes:
  ollama_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/kolay-box/ollama   # Block Storage Volume — survives droplet destroy
  webui_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/kolay-box/webui    # Block Storage Volume — survives droplet destroy
```

### [NEW] docker-compose.dev.yml

CPU-only override for local development without a GPU:

```yaml
# Usage: docker compose -f docker-compose.yml -f docker-compose.dev.yml up
services:
  ollama:
    deploy: {}                        # removes GPU reservation
    environment:
      - OLLAMA_NUM_GPU=0              # force CPU mode

volumes:
  ollama_data:
    driver: local                     # use local disk, not block storage
  webui_data:
    driver: local
```

With `gemma4:e4b` (6GB Q4) this runs on any laptop. Tool calling works, just slower.

### [NEW] Dockerfile.mcp

```dockerfile
FROM python:3.12-slim AS builder
RUN pip install uv
RUN uv pip install --system kolay-cli mcpo

FROM python:3.12-slim
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin/kolay-mcp /usr/local/bin/
COPY --from=builder /usr/local/bin/mcpo /usr/local/bin/
COPY mcpo.config.json /app/
EXPOSE 8000
CMD ["mcpo", "--config", "/app/mcpo.config.json", "--port", "8000"]
```

Installs `kolay-cli` from PyPI. The Box has no dependency on the local repo source.
To test unreleased CLI changes: `RUN pip install git+https://github.com/nicetunca/kolay-cli.git@branch`

### [NEW] mcpo.config.json

```json
{
  "mcpServers": {
    "kolay-ik": {
      "command": "kolay-mcp",
      "env": {
        "KOLAY_SECURITY_PROFILE": "standard"
      }
    }
  }
}
```

### [NEW] .env.example

```bash
# ── Kolay AI Box Configuration ─────────────────────────────────────

# LLM Model (Ollama identifier)
# gemma4:e4b   → demo / CPU / laptop (6GB VRAM)
# gemma4:26b   → PoC / production recommended (17GB VRAM Q4, MoE, fast)
# gemma4:31b   → max quality (20GB VRAM Q4)
# qwen2.5:32b  → fallback if Gemma tool-calling quality is insufficient
OLLAMA_MODEL=gemma4:26b

# Kolay IK API Token
# Optional here — can also be entered per-user in Open WebUI External Tools
# Get yours from: Kolay IK > Settings > API Tokens
KOLAY_API_TOKEN=

# Security profile
KOLAY_SECURITY_PROFILE=standard   # or "enterprise"

# Open WebUI
WEBUI_PORT=3000
WEBUI_SECRET_KEY=change-me-to-a-long-random-string
```

### [NEW] prompts/system.md

```markdown
You are a Kolay IK HR Assistant. You help HR managers and executives with
employee data, leave management, payroll queries, and workforce analytics.

RULES:
- ALWAYS use tools for HR data. NEVER guess employee information.
- If a tool returns an error, explain what went wrong and suggest a fix.
- For WRITE operations (leave requests, updates, deletions): always confirm
  with the user before executing. State exactly what will change.
- Respond in the same language the user writes in. Default to Turkish.
- When displaying employee lists, use clean markdown tables.
- Never reveal API tokens, internal IDs, or system metadata.

VISUALIZATION RULES:
- For diagrams (org charts, approval flows, onboarding timelines, Gantt):
  use Mermaid.js syntax inside ```mermaid blocks. Open WebUI renders natively.
- For data charts (bar, line, pie, doughnut, radar, scatter):
  generate a complete self-contained HTML artifact using Chart.js via CDN.
  Required structure:
    <!DOCTYPE html>
    <html><head><meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>body{margin:0;padding:16px} canvas{max-width:100%}</style>
    </head><body><canvas id="c"></canvas>
    <script>new Chart(document.getElementById('c'), { ... })</script>
    </body></html>
- ALWAYS use real data from tool call results. Never use placeholder data.
- Color palette: #1a73e8, #4285f4, #34a853, #fbbc04, #ea4335, #9aa0a6
- Label axes and legends in the same language as the user's query.
- Use Turkish number formatting (1.234,56) when the user writes in Turkish.

AVAILABLE CAPABILITIES:
- Search employees, view profiles, check leave balances
- Submit and manage leave requests
- View timelogs, overtime, attendance patterns
- Training records, expense reports, payroll data
- Organizational unit hierarchy and approval chains
- HR analytics: burnout risk, turnover scanning, anomaly detection
- Visualizations: pie/bar/line charts (Chart.js) and diagrams (Mermaid)
```

### [NEW] scripts/deploy.sh

```bash
#!/usr/bin/env bash
# Kolay AI Box — provision and launch
# Usage: ./scripts/deploy.sh
# Requires: doctl authenticated, SSH key configured

set -euo pipefail

DROPLET_NAME="kolay-ai-box"
VOLUME_NAME="kolay-box-data"
REGION="nyc2"
SIZE="gpu-rtx4000ada-1"    # $0.76/hr, 20GB VRAM, fits Gemma 4 26B Q4
IMAGE="docker-20-04"
SSH_KEY_ID="${KOLAY_SSH_KEY_ID:?Set KOLAY_SSH_KEY_ID}"

echo "[1/4] Ensuring volume exists..."
doctl compute volume create "$VOLUME_NAME" \
  --region "$REGION" \
  --size 20 \
  --fs-type ext4 2>/dev/null || echo "Volume already exists, continuing."

VOLUME_ID=$(doctl compute volume list --format ID,Name --no-header | grep "$VOLUME_NAME" | awk '{print $1}')

echo "[2/4] Creating droplet..."
DROPLET_ID=$(doctl compute droplet create "$DROPLET_NAME" \
  --size "$SIZE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --ssh-keys "$SSH_KEY_ID" \
  --wait \
  --format ID \
  --no-header)

echo "[3/4] Attaching volume..."
doctl compute volume-action attach "$VOLUME_ID" "$DROPLET_ID" --wait

DROPLET_IP=$(doctl compute droplet get "$DROPLET_ID" --format PublicIPv4 --no-header)

echo "[4/4] Droplet ready at $DROPLET_IP"
echo "Next steps:"
echo "  ssh root@$DROPLET_IP"
echo "  mkdir -p /mnt/kolay-box/{ollama,webui}"
echo "  mount /dev/sda /mnt/kolay-box  # or configured block device"
echo "  git clone <repo> && cd box && cp .env.example .env && docker compose up -d"
```

### [NEW] scripts/teardown.sh

```bash
#!/usr/bin/env bash
# Kolay AI Box — stop and destroy (no billing while idle)
# Data persists on the volume. Run deploy.sh to resume.

set -euo pipefail

DROPLET_NAME="kolay-ai-box"
VOLUME_NAME="kolay-box-data"

DROPLET_ID=$(doctl compute droplet list --format ID,Name --no-header | grep "$DROPLET_NAME" | awk '{print $1}')
VOLUME_ID=$(doctl compute volume list --format ID,Name --no-header | grep "$VOLUME_NAME" | awk '{print $1}')

DROPLET_IP=$(doctl compute droplet get "$DROPLET_ID" --format PublicIPv4 --no-header)

echo "[1/3] Stopping docker compose..."
ssh root@"$DROPLET_IP" "cd box && docker compose down"

echo "[2/3] Detaching volume (data is safe)..."
doctl compute volume-action detach "$VOLUME_ID" "$DROPLET_ID" --wait

echo "[3/3] Destroying droplet (billing stops now)..."
doctl compute droplet delete "$DROPLET_ID" --force

echo "Done. Volume '$VOLUME_NAME' is preserved. Run deploy.sh to resume."
echo "All chat history, model weights, and configs are intact."
```

### [NEW] scripts/doctor.sh

```bash
#!/usr/bin/env bash
# Kolay AI Box — health check
# Usage: ./scripts/doctor.sh

PASS="[PASS]"
FAIL="[FAIL]"

check() {
  local label=$1; local cmd=$2; local fix=$3
  if eval "$cmd" &>/dev/null; then
    echo "$PASS $label"
  else
    echo "$FAIL $label"
    echo "     Fix: $fix"
  fi
}

echo "=== Kolay AI Box Health Check ==="
check "Docker running"           "docker info"                                "Start Docker Desktop or systemctl start docker"
check "Compose services up"      "docker compose ps | grep -q running"        "docker compose up -d"
check "Ollama API reachable"     "curl -sf http://localhost:11434/api/tags"    "docker compose logs ollama"
check "Model pulled"             "curl -sf http://localhost:11434/api/tags | grep -q gemma4" "docker compose logs ollama | tail -50"
check "mcpo reachable"           "curl -sf http://localhost:8000/docs"         "docker compose logs mcpo"
check "Open WebUI reachable"     "curl -sf http://localhost:3000"              "docker compose logs open-webui"
check "Kolay IK API reachable"   "curl -sf https://api.kolayik.com/health"     "Check KOLAY_API_TOKEN in .env"
echo "================================="
```

### [NEW] README.md

```markdown
# Kolay AI Box

Self-hosted AI HR assistant. Gemma 4 + Kolay IK data. Deploy in 5 minutes.

## Deploy

git clone https://github.com/nicetunca/kolay-ai-box.git
cd kolay-ai-box/box
cp .env.example .env
# Edit .env: set WEBUI_SECRET_KEY to a random string
docker compose up -d

## Connect

1. Open http://localhost:3000
2. Create your admin account (first user becomes admin)
3. Admin Settings → External Tools → Add:
   - Type: OpenAPI | URL: http://mcpo:8000 | Auth: Bearer <your-kolay-ik-token>
4. Start chatting.

## Example queries

"Who is on leave this week?"
"Show me overtime hours by department as a bar chart"
"Draw the org chart for Engineering"
"Submit a leave request for Ayşe next Monday"

## Troubleshoot

./scripts/doctor.sh
```

---

## 9. What We DO NOT Build

| Item | Reason |
|------|--------|
| Custom chat UI | Open WebUI is production-ready, MIT-licensed |
| Token entry landing page | Deferred to Phase 2 — OWUI External Tools works for PoC |
| LLM provider abstraction | Ollama handles this natively |
| Chart rendering server | Chart.js is CDN-loaded by the LLM-generated HTML |
| Mermaid rendering server | Open WebUI renders it natively |
| `kolay_box` Python package | No new Python. Docker config + scripts + prompt. |
| BI dashboard (Metabase/Superset) | Deferred to Phase 3 |

---

## 10. Model Selection

Gemma 4 family (released April 2, 2026, Apache 2.0):

| Model | VRAM Q4 | Tool Calling | Use Case |
|-------|---------|--------------|---------|
| `gemma4:e4b` | ~6 GB | Good | Laptop demo, CPU mode |
| **`gemma4:26b`** | **~17 GB** | **Strong** | **PoC default — MoE, fast, fits RTX 4000 Ada** |
| `gemma4:31b` | ~20 GB | Best | Production when quality matters most |
| `qwen2.5:32b` | ~20 GB | Strong | Fallback if Gemma tool-calling is insufficient |

Default: `gemma4:26b`. Change one line in `.env` to swap.

---

## 11. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gemma 4 26B tool-calling quality poor in Turkish | High | PoC will surface this. Fallback: `qwen2.5:32b`. Prompt-tuning is the first lever. |
| Open WebUI Artifacts rendering unstable | Medium | Fallback: markdown tables always work. Chart.js is a progressive enhancement. |
| DO RTX 4000 Ada (20GB VRAM) too tight for 26B Q4 | Low | Q4 is ~17GB. 3GB headroom. Context window may be limited at high load. |
| OWUI MCP/Artifacts breaking in an update | Medium | Pin OWUI version. mcpo provides stable abstraction layer. |
| Model auto-pull fails on first boot | Low | Resolved — init entrypoint pulls before health check passes. |

---

## 12. Open Questions

> [!IMPORTANT]
> **Per-user vs global token.** OWUI per-user tool config requires each user to enter their own
> token. Should `.env` support a global `KOLAY_API_TOKEN` fallback for single-tenant deployments?
> Simplifies setup but all users share one token's permission level.

---

## 13. Verification Plan

### Automated
```bash
docker compose config          # validates compose syntax
docker compose build mcpo      # Dockerfile builds clean
shellcheck scripts/doctor.sh   # shell script linting
shellcheck scripts/deploy.sh
shellcheck scripts/teardown.sh
```

### Manual end-to-end (PoC sign-off)

1. `./scripts/deploy.sh` — provision DO RTX 4000 Ada + attach volume
2. SSH in, mount volume, `docker compose up -d`
3. `docker compose logs ollama` — verify `gemma4:26b` pulled successfully
4. Open `http://<droplet-ip>:3000` → create admin account
5. Admin Settings → External Tools → add Kolay MCP (URL + Bearer token)
6. Chat test — tool calling: `"Show me all active employees"` → list appears
7. Chart test: `"Show leave usage by department as a pie chart"` → Chart.js artifact renders
8. Diagram test: `"Draw the org chart for Engineering"` → Mermaid renders inline
9. Write test: `"Submit leave for next Monday"` → confirmation prompt appears, executes
10. `./scripts/doctor.sh` → all checks pass
11. `./scripts/teardown.sh` → droplet destroyed, volume preserved
12. `./scripts/deploy.sh` again → resume, all data intact (chat history, model weights, configs)

---

## 14. PoC Execution Timeline

```
Day 1  Provision DO droplet. Mount block volume. docker compose up -d.
       Verify Gemma 4 26B pulls and serves via Ollama.

Day 2  Connect Open WebUI → mcpo → Kolay MCP.
       First tool-calling test: "List active employees"

Day 3  System prompt tuning. Visualization tests.
       Pie chart, bar chart, Mermaid org chart.

Day 4  Turkish HR query testing. Edge cases.
       write operations with confirmation flow.

Day 5  doctor.sh + deploy/teardown scripts. README. Demo recording.
       teardown → redeploy → verify data persistence.
```

**Target:** Working demo in hand by end of Day 5. Cost: ~$30 total (40 hours × $0.76/hr + $2 volume).
