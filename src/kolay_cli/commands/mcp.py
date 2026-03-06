"""
``kolay mcp`` — MCP server management commands.
"""
from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="Manage the Kolay IK MCP server for AI/LLM integration.")
console = Console(highlight=False)

_PRIMARY = "#376BFB"


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    from ..ui import no_command_help
    no_command_help(ctx)


@app.command(name="serve")
def serve(
    transport: str = typer.Option(
        "stdio",
        "--transport", "-t",
        help="Transport protocol: 'stdio' (default, for Claude Desktop / local) or 'http' (for remote / multi-client).",
    ),
    host: str = typer.Option("127.0.0.1", "--host", help="Host for HTTP transport."),
    port: int = typer.Option(8000, "--port", "-p", help="Port for HTTP transport."),
) -> None:
    """Start the Kolay IK MCP server.

    \b
    STDIO mode (default) — use with Claude Desktop, Cursor, Gemini CLI:
        kolay mcp serve

    HTTP mode — expose as a network endpoint:
        kolay mcp serve --transport http --port 8000

    \b
    Claude Desktop config (~/.claude/claude_desktop_config.json):
        {
          "mcpServers": {
            "kolay-ik": {
              "command": "kolay",
              "args": ["mcp", "serve"]
            }
          }
        }
    """
    try:
        from ..mcp_server import mcp
    except ImportError:
        console.print(
            "\n[bold red]fastmcp is not installed.[/bold red]\n"
            f"  Install it with: [bold {_PRIMARY}]pip install 'kolay-cli[mcp]'[/bold {_PRIMARY}]\n"
        )
        raise typer.Exit(1)

    if transport == "http":
        console.print(
            f"\n[bold {_PRIMARY}]🔌 Kolay IK MCP server[/bold {_PRIMARY}]  "
            f"[grey62]http://{host}:{port}/mcp[/grey62]\n"
        )
        mcp.run(transport="http", host=host, port=port)
    else:
        # STDIO — no banner (would corrupt the JSON stream)
        mcp.run()


@app.command(name="tools")
def list_tools() -> None:
    """Print all available MCP tools registered on the server."""
    try:
        from ..mcp_server import mcp
    except ImportError:
        console.print(
            "\n[bold red]fastmcp is not installed.[/bold red]\n"
            f"  Install it with: [bold {_PRIMARY}]pip install 'kolay-cli[mcp]'[/bold {_PRIMARY}]\n"
        )
        raise typer.Exit(1)

    import asyncio
    from rich.table import Table

    tools = asyncio.run(mcp.list_tools())
    table = Table(
        header_style=f"bold {_PRIMARY}", border_style=_PRIMARY,
        box=None, show_edge=False,
    )
    table.add_column("#", style="grey62", justify="right", width=4)
    table.add_column("Tool", style="bold white", min_width=28)
    table.add_column("Description", style="grey85")

    for i, tool in enumerate(sorted(tools, key=lambda t: t.name), 1):
        desc = (tool.description or "").split("\n")[0][:80]
        table.add_row(str(i), tool.name, desc)

    console.print(f"\n[bold {_PRIMARY}]🔧 Kolay IK MCP Tools[/bold {_PRIMARY}] [grey62]({len(tools)} registered)[/grey62]\n")
    console.print(table)
    console.print()


@app.command(name="install")
def install() -> None:
    """Install the Kolay IK MCP server into supported LLM Desktop clients.
    
    Currently supports:
      - Claude Desktop (macOS/Windows)
      - Cursor IDE (project-specific)
      - Windsurf
    """
    import sys
    import json
    from ..services.mcp_registry import install_mcp_server
    
    # We use sys.executable to ensure we call the same python environment
    cmd = sys.executable
    args = ["-m", "kolay_cli.mcp_server"]
    
    console.print(f"\n[bold {_PRIMARY}]🚀 Installing Kolay MCP Server[/bold {_PRIMARY}]")
    
    results = install_mcp_server("kolay-ik", cmd, args)
    
    success_count = 0
    for client_name, success, msg in results:
        if success:
            console.print(f"  [green]✔[/green] [bold]{client_name}[/bold]: Successfully configured.")
            console.print(f"      [grey62]→ {msg}[/grey62]")
            success_count += 1
        else:
            if "Unsupported platform" in msg or "not determinable" in msg:
                console.print(f"  [grey50]○[/grey50] [bold grey62]{client_name}[/bold grey62]: Skipped ({msg})")
            else:
                console.print(f"  [red]✖[/red] [bold]{client_name}[/bold]: Failed to configure.")
                console.print(f"      [red]→ {msg}[/red]")
                
    if success_count > 0:
        console.print("\n[green]✅ Installation complete![/green] Please restart your client(s) to apply changes.\n")
    else:
        console.print(f"\n[yellow]⚠️  No active clients were automatically configured.[/yellow]")
        console.print(f"   You can manually add the server using:\n   [bold]Command:[/bold] {cmd}\n   [bold]Args:[/bold] {json.dumps(args)}\n")
