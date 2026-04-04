#!/usr/bin/env bash
# ── Kolay AI Box — Diagnose ─────────────────────────────────────────
# Checks every component and tells you exactly how to fix failures.
# Usage: make diagnose  (or: ./bin/diagnose.sh)

set -uo pipefail
cd "$(dirname "$0")/.."

PASS="\033[32m[PASS]\033[0m"
FAIL="\033[31m[FAIL]\033[0m"
WARN="\033[33m[WARN]\033[0m"
INFO="\033[34m[INFO]\033[0m"

passed=0
failed=0

check() {
  local label="$1"
  local cmd="$2"
  local fix="$3"

  if eval "$cmd" &>/dev/null; then
    echo -e "$PASS $label"
    passed=$((passed+1))
  else
    echo -e "$FAIL $label"
    echo -e "       Fix: $fix"
    failed=$((failed+1))
  fi
}

warn() {
  local label="$1"
  local detail="$2"
  echo -e "$WARN $label"
  echo -e "       $detail"
}

echo ""
echo "=== Kolay AI Box — System Diagnostics ==="
echo ""

# ── Prerequisites ────────────────────────────────────────────────
check "Docker daemon running" \
  "docker info" \
  "Start Docker: 'open -a Docker' (Mac) or 'sudo systemctl start docker' (Linux)"

check "Docker Compose available" \
  "docker compose version" \
  "Install Docker Compose: https://docs.docker.com/compose/install/"

# ── Config ───────────────────────────────────────────────────────
check ".env file exists" \
  "test -f .env" \
  "Run: cp .env.example .env && edit .env with your settings"

if [ -f .env ]; then
  check "WEBUI_SECRET_KEY is set" \
    "grep -q 'WEBUI_SECRET_KEY=.' .env && ! grep -q 'WEBUI_SECRET_KEY=change-me' .env" \
    "Edit .env: set WEBUI_SECRET_KEY to a random string (e.g. openssl rand -hex 32)"

  if grep -q 'KOLAY_API_TOKEN=.' .env 2>/dev/null; then
    echo -e "$PASS KOLAY_API_TOKEN configured in .env"
    ((passed++))
  else
    warn "KOLAY_API_TOKEN not set in .env" \
      "OK if you plan to enter tokens per-user in Open WebUI settings."
  fi
fi

# ── Containers ───────────────────────────────────────────────────
check "Ollama container present" \
  "docker compose ps --format json 2>/dev/null | grep -q ollama" \
  "Run: make up (or: docker compose up -d)"

check "Open WebUI container present" \
  "docker compose ps --format json 2>/dev/null | grep -q webui" \
  "Run: make up  |  Check logs: docker compose logs open-webui"

check "Proxy container present" \
  "docker compose ps --format json 2>/dev/null | grep -q proxy" \
  "Run: make up  |  Check logs: docker compose logs proxy"

# ── Services ─────────────────────────────────────────────────────
check "Ollama API responding" \
  "curl -sf http://localhost:11434/api/tags" \
  "Ollama may still be starting. Wait 30s, or check: docker compose logs ollama"

check "Model loaded (gemma4)" \
  "curl -sf http://localhost:11434/api/tags | grep -q gemma" \
  "Model still pulling. Check progress: docker compose logs ollama --tail 20"

check "Proxy/mcpo API responding" \
  "curl -sf http://localhost:8000/docs" \
  "Check logs: docker compose logs proxy"

check "Open WebUI responding" \
  "curl -sf http://localhost:${WEBUI_PORT:-3000}" \
  "Check logs: docker compose logs open-webui  |  Ollama may not be healthy yet."

# ── External ─────────────────────────────────────────────────────
check "Kolay IK API reachable" \
  "[ \"\$(curl -so /dev/null -w '%{http_code}' --max-time 5 https://api.kolayik.com)\" != '000' ]" \
  "Check your internet connection. If behind a firewall, allow outbound HTTPS to api.kolayik.com"

# ── Summary ──────────────────────────────────────────────────────
echo ""
echo "=== Results: $passed passed, $failed failed ==="

if [ "$failed" -eq 0 ]; then
  echo -e "$INFO All systems operational. Open http://localhost:${WEBUI_PORT:-3000} to start."
else
  echo -e "$INFO Fix the items above and run 'make diagnose' again."
fi

echo ""
exit "$failed"
