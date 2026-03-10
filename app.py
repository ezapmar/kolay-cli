"""
Railway entry point for the Kolay IK MCP server.

Railway auto-detects this file and runs it with `python app.py`.
The server listens on the PORT env var (provided by Railway) and
binds to 0.0.0.0 so it is reachable from outside the container.

Environment variables:
  KOLAY_API_TOKEN  – your Kolay IK API token  (required)
  MCP_API_KEY      – secret for X-API-Key auth (required — server won't start without it)
  PORT             – Railway sets this automatically (default: 8080)

Connection URL:
  https://<your-domain>/mcp

  Clients like Mistral Le Chat or OpenAI connect to /mcp.
  Every request must include:
      Header:  X-API-Key: <your MCP_API_KEY value>
"""
from __future__ import annotations

import os
import sys
import warnings

# ── Silence upstream deprecation from websockets 16.x ──
# FastMCP 3.x still imports websockets.legacy internally.
# This is harmless and will be resolved in a future FastMCP release.
warnings.filterwarnings("ignore", message="websockets.legacy is deprecated")

# ── FastMCP log suppression (must be set before import) ──
os.environ.setdefault("FASTMCP_LOG_LEVEL", "WARNING")
os.environ.setdefault("FASTMCP_SHOW_SERVER_BANNER", "False")

import uvicorn  # noqa: E402
from kolay_cli.mcp_server import create_secured_http_app  # noqa: E402

# ── Enforce MCP_API_KEY — refuse to start without it ──
api_key = os.environ.get("MCP_API_KEY")
if not api_key:
    print(
        "\n❌ FATAL: MCP_API_KEY environment variable is not set.\n"
        "   The server refuses to start without authentication.\n"
        "   Set it in your Railway dashboard: Settings → Variables → MCP_API_KEY\n"
    )
    sys.exit(1)

# ── Railway / container port binding ──
host = "0.0.0.0"
port = int(os.environ.get("PORT", 8080))
app = create_secured_http_app()

if __name__ == "__main__":
    print(f"\n🔌 Kolay IK MCP server")
    print(f"   Endpoint:  http://{host}:{port}/mcp")
    print(f"   Auth:      ✔ enabled (X-API-Key required)")
    print(f"   Key hint:  {api_key[:4]}...{api_key[-4:]}\n")
    uvicorn.run(app, host=host, port=port)
