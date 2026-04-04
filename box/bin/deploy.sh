#!/usr/bin/env bash
# ── Kolay AI Box — Deploy to DigitalOcean ────────────────────────────
# Idempotent: safe to run multiple times.
# Creates a persistent volume (if needed), spins up a GPU droplet,
# attaches the volume, and prints next steps.
#
# Prerequisites:
#   brew install doctl && doctl auth init
#   export KOLAY_SSH_KEY_ID=<your-ssh-key-fingerprint>
#
# Usage: make deploy  (or: ./bin/deploy.sh)

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────
DROPLET_NAME="${KOLAY_DROPLET_NAME:-kolay-ai-box}"
VOLUME_NAME="${KOLAY_VOLUME_NAME:-kolay-box-data}"
REGION="${KOLAY_REGION:-nyc2}"
SIZE="${KOLAY_DROPLET_SIZE:-gpu-rtx4000ada-1}"   # $0.76/hr, 20GB VRAM
IMAGE="docker-20-04"
SSH_KEY_ID="${KOLAY_SSH_KEY_ID:?[deploy] Set KOLAY_SSH_KEY_ID (doctl compute ssh-key list)}"

echo ""
echo "=== Kolay AI Box — Cloud Deploy ==="
echo ""

# ── Step 1: Volume ───────────────────────────────────────────────
echo "[1/4] Ensuring block storage volume '$VOLUME_NAME' exists..."
if doctl compute volume list --format Name --no-header | grep -q "^${VOLUME_NAME}$"; then
  echo "       Volume already exists. Reusing."
else
  doctl compute volume create "$VOLUME_NAME" \
    --region "$REGION" \
    --size 20GiB \
    --fs-type ext4
  echo "       Volume created (20GB, ext4)."
fi

VOLUME_ID=$(doctl compute volume list --format ID,Name --no-header | grep "$VOLUME_NAME" | awk '{print $1}')

# ── Step 2: Droplet ──────────────────────────────────────────────
echo "[2/4] Creating GPU droplet '$DROPLET_NAME' ($SIZE)..."
if doctl compute droplet list --format Name --no-header | grep -q "^${DROPLET_NAME}$"; then
  echo "       Droplet already exists. Skipping creation."
  DROPLET_ID=$(doctl compute droplet list --format ID,Name --no-header | grep "$DROPLET_NAME" | awk '{print $1}')
else
  DROPLET_ID=$(doctl compute droplet create "$DROPLET_NAME" \
    --size "$SIZE" \
    --image "$IMAGE" \
    --region "$REGION" \
    --ssh-keys "$SSH_KEY_ID" \
    --wait \
    --format ID \
    --no-header)
  echo "       Droplet created."
fi

# ── Step 3: Attach ───────────────────────────────────────────────
echo "[3/4] Attaching volume to droplet..."
doctl compute volume-action attach "$VOLUME_ID" "$DROPLET_ID" --wait 2>/dev/null || \
  echo "       Volume may already be attached. Continuing."

# ── Step 4: Summary ─────────────────────────────────────────────
DROPLET_IP=$(doctl compute droplet get "$DROPLET_ID" --format PublicIPv4 --no-header)

echo "[4/4] Ready."
echo ""
echo "=== Next Steps ==="
echo ""
echo "  1. SSH into the droplet:"
echo "     ssh root@$DROPLET_IP"
echo ""
echo "  2. Mount the volume and start the stack:"
echo "     mkdir -p /mnt/kolay-box/{ollama,webui}"
echo "     mount -o defaults,nofail,discard /dev/disk/by-id/scsi-0DO_Volume_${VOLUME_NAME} /mnt/kolay-box"
echo "     git clone https://github.com/nicetunca/kolay-cli.git"
echo "     cd kolay-cli/box"
echo "     cp .env.example .env"
echo "     # Edit .env: set WEBUI_SECRET_KEY and optionally KOLAY_API_TOKEN"
echo "     make up"
echo ""
echo "  3. Open in browser:"
echo "     http://$DROPLET_IP:3000"
echo ""
echo "  Billing: \$${SIZE##*-} at \$0.76/hr. Run 'make cloud-down' to stop billing."
echo ""
