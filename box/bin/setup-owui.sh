#!/usr/bin/env bash
# ── Kolay AI Box — First Boot Setup ─────────────────────────────────
# 1. Creates admin account
# 2. Registers Kolay proxy as Tool Server
# 3. Forces OWUI to load tools (always POSTs, even if already registered)
#
# Runs as a Docker container, then exits. Safe to re-run.

set -uo pipefail

# All URLs and credentials are read inside Python via os.environ —
# never interpolated into inline code (prevents shell injection).

# ── Wait for Open WebUI ─────────────────────────────────────────────
echo "[setup] Waiting for Open WebUI (up to 6 minutes on first boot)..."
for i in $(seq 1 120); do
  code=$(python3 -c "
import os, urllib.request
try:
    r = urllib.request.urlopen(os.environ['OWUI_URL'] + '/health', timeout=3)
    print(r.getcode())
except: print(0)
" 2>/dev/null)
  [ "$code" = "200" ] && break
  [ $((i % 10)) -eq 0 ] && echo "[setup]   not ready yet ($i/120)..."
  sleep 3
done
echo "[setup] Open WebUI is up."

# ── Also wait for proxy ─────────────────────────────────────────────
echo "[setup] Waiting for Kolay proxy..."
for i in $(seq 1 30); do
  ok=$(python3 -c "
import os, urllib.request
try:
    r = urllib.request.urlopen(os.environ['PROXY_URL'] + '/kolay-ik/openapi.json', timeout=3)
    print('ok' if r.getcode() == 200 else 'no')
except: print('no')
" 2>/dev/null)
  [ "$ok" = "ok" ] && break
  sleep 2
done
echo "[setup] Proxy is ready."

# ── Authenticate ────────────────────────────────────────────────────
export TOKEN=$(python3 - <<'PYEOF'
import urllib.request, json, sys, os

base = os.environ['OWUI_URL']
email = os.environ['ADMIN_EMAIL']
password = os.environ['ADMIN_PASS']
name = os.environ['ADMIN_NAME']

def post(url, data):
    req = urllib.request.Request(
        url, data=json.dumps(data).encode(),
        headers={'Content-Type': 'application/json'}
    )
    try:
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read()), r.getcode()
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read())
        except: body = {}
        return body, e.code

# Signin first (restarts)
body, code = post(f"{base}/api/v1/auths/signin", {"email": email, "password": password})
if code == 200 and body.get("token"):
    print(body["token"]); sys.exit(0)

# Signup (first boot)
body, code = post(f"{base}/api/v1/auths/signup", {
    "name": name, "email": email, "password": password, "profile_image_url": ""
})
if code == 200 and body.get("token"):
    print(body["token"]); sys.exit(0)

sys.exit(1)
PYEOF
)

if [ -z "${TOKEN:-}" ]; then
  echo "[setup] Auth failed. Check ADMIN_EMAIL / ADMIN_PASS in .env."
  exit 1
fi
echo "[setup] Authenticated."

# ── Register Tool Server (always POST to force reload) ──────────────
RESULT=$(python3 - <<'PYEOF'
import urllib.request, json, os, sys

base = os.environ['OWUI_URL']
token = os.environ['TOKEN']
proxy_url = os.environ['PROXY_URL']

headers_auth = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

def req(method, url, data=None):
    r = urllib.request.Request(
        url, data=json.dumps(data).encode() if data else None,
        headers=headers_auth, method=method
    )
    try:
        resp = urllib.request.urlopen(r, timeout=15)
        return json.loads(resp.read()), resp.getcode()
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read())
        except: body = {"error": str(e)}
        return body, e.code

# Always POST the full config — this forces OWUI to re-fetch the OpenAPI
# schema and hot-reload all tools into app.state.TOOL_SERVERS.
connection = {
    "url": proxy_url,
    "path": "/kolay-ik/openapi.json",
    "type": "openapi",
    "auth_type": "none",
    "key": None,
    "headers": None,
    "config": {"enable": True},
}

result, code = req('POST', f"{base}/api/v1/configs/tool_servers", {
    "TOOL_SERVER_CONNECTIONS": [connection]
})

if code == 200:
    print("ok")
else:
    print(f"fail:{code}", file=sys.stderr)
    sys.exit(1)
PYEOF
)

if [ "$RESULT" = "ok" ]; then
  echo "[setup] Kolay tools registered and loaded."
else
  echo "[setup] Tool registration failed. Manual step:"
  echo "[setup]   Admin Settings > Tools > Add Tool Server"
  echo "[setup]   URL: ${PROXY_URL}  Path: /kolay-ik/openapi.json"
fi

# ── Cleanup: delete any leftover workspace model ────────────────────
# Previous versions created a "kolay-hr" workspace model. Remove it
# so users only see the raw Gemma model in the selector.
python3 - <<'PYEOF'
import urllib.request, json, os
base = os.environ['OWUI_URL']
token = os.environ['TOKEN']
r = urllib.request.Request(
    f"{base}/api/v1/models/delete?id=kolay-hr",
    headers={'Authorization': f'Bearer {token}'},
    method='DELETE'
)
try:
    urllib.request.urlopen(r, timeout=5)
    print("[setup] Cleaned up old workspace model.")
except:
    pass  # model didn't exist, that's fine
PYEOF

echo ""
echo "[setup] Done. Open http://localhost:${WEBUI_PORT:-3000} to start."
echo "[setup] System prompt is set via DEFAULT_SYSTEM_PROMPT in compose.yml."
echo ""
