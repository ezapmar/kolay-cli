#!/bin/sh
# ── Kolay AI Box — Proxy Entrypoint ─────────────────────────────────
# Generates mcpo.json at runtime so container env vars (especially
# KOLAY_API_TOKEN) are explicitly passed to the kolay-mcp subprocess.
#
# Why: mcpo spawns kolay-mcp as a child process. The "env" block in
# mcpo.json controls what env vars the child sees. A static mcpo.json
# baked into the image can't reference runtime env vars. This script
# writes the config at boot with the actual values.

set -eu

cat > /app/mcpo.json << EOF
{
  "mcpServers": {
    "kolay-ik": {
      "command": "kolay-mcp",
      "env": {
        "KOLAY_API_TOKEN": "${KOLAY_API_TOKEN:-}",
        "KOLAY_SECURITY_PROFILE": "${KOLAY_SECURITY_PROFILE:-standard}"
      }
    }
  }
}
EOF

echo "[proxy] mcpo.json generated. Token present: $([ -n "${KOLAY_API_TOKEN:-}" ] && echo yes || echo no)"
exec mcpo --config /app/mcpo.json --port 8000
