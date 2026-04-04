"""python -m kolay_mcp — run the Kolay IK MCP server.

Delegates to the same startup logic as `kolay-mcp` entry point.
Supports both STDIO (default) and HTTP transport.

Examples:
    python -m kolay_mcp                           # stdio for Claude/Cursor
    python -m kolay_mcp --transport http           # HTTP for network deploy
    python -m kolay_mcp --transport http --port 9000
"""
from __future__ import annotations

import argparse
import os
import sys


def main() -> None:
    from kolay_mcp import mcp, create_secured_http_app

    default_port = int(os.environ.get("PORT", 8000))

    parser = argparse.ArgumentParser(
        prog="kolay-mcp",
        description="Kolay IK MCP server — connect any AI client to your HR platform.",
    )
    parser.add_argument(
        "--transport", choices=["stdio", "http"], default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host", default="0.0.0.0" if "PORT" in os.environ else "127.0.0.1",
        help="Bind address for HTTP transport",
    )
    parser.add_argument(
        "--port", type=int, default=default_port,
        help=f"Port for HTTP transport (default: {default_port})",
    )
    args = parser.parse_args()

    if args.transport == "http":
        try:
            import uvicorn
        except ImportError:
            print(
                "\n"
                "  kolay-mcp: HTTP transport requires uvicorn.\n"
                "\n"
                "  Fix:\n"
                "    pip install uvicorn\n"
                "\n",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"\n  Kolay IK MCP server  http://{args.host}:{args.port}/mcp\n")
        app = create_secured_http_app()
        uvicorn.run(app, host=args.host, port=args.port)

    elif sys.stdin.isatty():
        # User ran directly in terminal — friendly guidance
        print(
            "\n"
            "  Kolay IK MCP Server\n"
            "\n"
            "  This is for AI clients (Claude, Cursor, Gemini CLI, ChatGPT).\n"
            "  For the human CLI:  kolay --help\n"
            "\n"
            "  Network mode:\n"
            "    python -m kolay_mcp --transport http\n"
            "\n"
            "  Claude Desktop config:\n"
            '    { "mcpServers": { "kolay-ik": { "command": "kolay-mcp" } } }\n'
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
