"""
Railway entry point for the Kolay IK MCP server.

Railway auto-detects this file and runs it with `python app.py`.
The server listens on the PORT env var (provided by Railway) and
binds to 0.0.0.0 so it is reachable from outside the container.

Environment variables required:
  KOLAY_API_TOKEN  – your Kolay IK API token
  MCP_API_KEY      – secret to protect the public endpoint (X-API-Key header)

Optional:
  PORT             – Railway sets this automatically (default: 8080)
"""
from __future__ import annotations

import os
import uvicorn

# These must be set before FastMCP initialises logging.
os.environ.setdefault("FASTMCP_LOG_LEVEL", "WARNING")
os.environ.setdefault("FASTMCP_SHOW_SERVER_BANNER", "False")

from kolay_cli.mcp_server import create_secured_http_app  # noqa: E402

host = "0.0.0.0"
port = int(os.environ.get("PORT", 8080))

if __name__ == "__main__":
    print(f"\n🔌 Kolay IK MCP server  http://{host}:{port}/mcp\n")
    app = create_secured_http_app()
    uvicorn.run(app, host=host, port=port)
