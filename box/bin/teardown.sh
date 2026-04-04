#!/usr/bin/env bash
# ── Kolay AI Box — Teardown (Stop Billing) ───────────────────────────
# Stops containers, detaches volume, destroys droplet.
# Volume is preserved — all data (chats, models, configs) survives.
# Run deploy.sh to resume exactly where you left off.
#
# Usage: make cloud-down  (or: ./bin/teardown.sh)

set -euo pipefail

DROPLET_NAME="${KOLAY_DROPLET_NAME:-kolay-ai-box}"
VOLUME_NAME="${KOLAY_VOLUME_NAME:-kolay-box-data}"

echo ""
echo "=== Kolay AI Box — Teardown ==="
echo ""

# ── Find resources ───────────────────────────────────────────────
DROPLET_LINE=$(doctl compute droplet list --format ID,Name,PublicIPv4 --no-header | grep "$DROPLET_NAME" || true)

if [ -z "$DROPLET_LINE" ]; then
  echo "[SKIP] No droplet named '$DROPLET_NAME' found. Nothing to tear down."
  exit 0
fi

DROPLET_ID=$(echo "$DROPLET_LINE" | awk '{print $1}')
DROPLET_IP=$(echo "$DROPLET_LINE" | awk '{print $3}')

VOLUME_ID=$(doctl compute volume list --format ID,Name --no-header | grep "$VOLUME_NAME" | awk '{print $1}' || true)

# ── Step 1: Stop containers ─────────────────────────────────────
echo "[1/3] Stopping containers on $DROPLET_IP..."
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new root@"$DROPLET_IP" \
  "cd kolay-cli/box && docker compose down 2>/dev/null" 2>/dev/null || \
  echo "       Could not SSH. Proceeding with destroy anyway."

# ── Step 2: Detach volume ────────────────────────────────────────
if [ -n "$VOLUME_ID" ]; then
  echo "[2/3] Detaching volume (your data is safe)..."
  doctl compute volume-action detach "$VOLUME_ID" "$DROPLET_ID" --wait 2>/dev/null || \
    echo "       Volume may already be detached."
else
  echo "[2/3] No volume found. Skipping detach."
fi

# ── Step 3: Destroy droplet ──────────────────────────────────────
echo "[3/3] Destroying droplet (billing stops now)..."
doctl compute droplet delete "$DROPLET_ID" --force

echo ""
echo "=== Teardown Complete ==="
echo ""
echo "  Volume '$VOLUME_NAME' is preserved with all your data:"
echo "    - Chat history and conversations"
echo "    - Model weights (no re-download needed)"
echo "    - User accounts and tool configs"
echo "    - Generated charts and diagrams"
echo ""
echo "  Run 'make cloud-up' to resume where you left off."
echo ""
