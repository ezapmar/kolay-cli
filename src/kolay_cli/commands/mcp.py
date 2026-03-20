"""MCP server management commands."""
from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="Manage the Kolay IK MCP server for AI/LLM integration.")
console = Console(highlight=False)

from ..ui.constants import PRIMARY as _PRIMARY
_home = __import__("pathlib").Path.home()


def _tilde(path: str) -> str:
    """Replace the home directory prefix with ~ for display."""
    return path.replace(str(_home), "~")


@app.callback(invoke_without_command=True)
def _hint(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        # Issue #7: surface the most useful next step before the countdown
        console.print(
            f"\n[bold {_PRIMARY}]New here?[/bold {_PRIMARY}]  "
            f"Run [bold]kolay mcp install[/bold] to connect your AI client.\n"
        )
    from ..ui import no_command_help
    no_command_help(ctx)


import os

@app.command(name="serve")
def serve(
    transport: str = typer.Option(
        "stdio",
        "--transport", "-t",
        help="Transport protocol: 'stdio' (default, for Claude Desktop / local) or 'http' (for remote / multi-client).",
    ),
    host: str = typer.Option(
        "0.0.0.0" if "PORT" in os.environ else "127.0.0.1", 
        "--host", 
        help="Host for HTTP transport."
    ),
    port: int = typer.Option(
        int(os.environ.get("PORT", 8000)), 
        "--port", "-p", 
        help="Port for HTTP transport."
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Start the MCP server with a mocked API client (no network requests).",
    ),
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
            f" Install it with: [bold {_PRIMARY}]pip install 'kolay-cli[mcp]'[/bold {_PRIMARY}]\n"
        )
        raise typer.Exit(1)

    if mock:
        from ..api.mock_client import MockKolayClient
        from ..api import client as api_client
        import sys
        
        # Globally monkey-patch KolayClient for the isolated mock mode
        api_client.KolayClient = MockKolayClient  # type: ignore
        sys.modules["kolay_cli.api.client"].KolayClient = MockKolayClient

    if transport == "http":
        from ..mcp_server import create_secured_http_app
        import uvicorn

        api_key_status = "[green]enabled[/green]" if __import__("os").environ.get("MCP_API_KEY") else "[yellow]disabled[/yellow] (set MCP_API_KEY to secure)"
        console.print(
            f"\n[bold {_PRIMARY}]Kolay IK MCP server[/bold {_PRIMARY}]  "
            f"[grey62]http://{host}:{port}/mcp[/grey62]"
            f"\n   Auth: {api_key_status}\n"
        )
        app = create_secured_http_app()
        uvicorn.run(app, host=host, port=port)
    else:
        # STDIO — no banner (would corrupt the JSON stream)
        mcp.run()


@app.command(name="inspect")
def inspect() -> None:
    """List all available MCP tools with their signatures and permissions."""
    try:
        from ..mcp_server import mcp
    except ImportError:
        console.print(
            "\n[bold red]fastmcp is not installed.[/bold red]\n"
            f" Install it with: [bold {_PRIMARY}]pip install 'kolay-cli[mcp]'[/bold {_PRIMARY}]\n"
        )
        raise typer.Exit(1)

    import asyncio
    from rich.table import Table

    tools = asyncio.run(mcp.list_tools())
    table = Table(
        header_style=f"bold {_PRIMARY}", border_style=_PRIMARY,
        box=None, show_edge=False,
    )
    table.add_column("Type", style="bold", justify="center", width=7)
    table.add_column("Tool", style="bold white", min_width=22)
    table.add_column("Signature", style="cyan", min_width=20)
    table.add_column("Description", style="grey85")

    for tool in sorted(tools, key=lambda t: t.name):
        is_write = any(w in tool.name.lower() for w in ("create", "update", "delete", "terminate", "rehire"))
        tag = "[red]WRITE[/red]" if is_write else "[green]READ[/green]"
        
        props = tool.parameters.get("properties", {}) if tool.parameters else {}
        req = set(tool.parameters.get("required", [])) if getattr(tool, "parameters", None) else set()
        
        params = []
        for pk, pv in props.items():
            star = "*" if pk in req else ""
            
            # parse out complex types like anyOf or lists
            t = pv.get("type", "any")
            if isinstance(t, list):
                t = " | ".join(t)
            elif "anyOf" in pv:
                t = " | ".join([sub.get("type", "any") for sub in pv["anyOf"]])
            
            params.append(f"{pk}{star}: {t}")
        sig = ", ".join(params)
        
        desc = (tool.description or "").split("\n")[0][:60]
        table.add_row(tag, tool.name, sig, desc)

    console.print(f"\n[bold {_PRIMARY}]MCP Tool Inspector[/bold {_PRIMARY}] [grey62]({len(tools)} tools registered)[/grey62]\n")
    console.print(table)
    console.print(" [grey62]* indicates a required parameter[/grey62]\n")


@app.command(name="install")
def install(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip interactive picker and install for all supported clients."),
) -> None:
    """Install the Kolay IK MCP server into AI/LLM desktop clients.

    Interactively choose which client(s) to configure, or pass --yes to
    install for every supported client at once.

    \b
    Supported clients:
      • Claude Desktop      (macOS, Windows)
      • Cursor (global)     (~/.cursor/mcp.json)
      • Cursor (project)    (.cursor/mcp.json in cwd)
      • Windsurf            (~/.codeium/windsurf/mcp_config.json)
      • Gemini CLI          (~/.gemini/settings.json)
      • VS Code (Copilot)   (user-level mcp.json)
      • Zed                 (~/.config/zed/settings.json)
    """
    import sys
    import json
    from rich.table import Table
    from ..services.mcp_registry import get_strategies, install_mcp_server

    cmd = sys.executable
    args = ["-m", "kolay_cli.mcp_server"]

    strategies = get_strategies()

    console.print(f"\n[bold {_PRIMARY}]Kolay IK MCP Server Installer[/bold {_PRIMARY}]\n")


    if not yes:
        # Issue #1 & #2: single-line rows — no_wrap + ellipsis on description
        table = Table(
            header_style=f"bold {_PRIMARY}",
            box=None, show_edge=False, show_header=True,
            padding=(0, 2),
        )
        table.add_column("#", style="grey62", justify="right", width=3, no_wrap=True)
        table.add_column("Client", style="bold white", min_width=20, max_width=22, no_wrap=True)
        table.add_column("Details", style="grey85", no_wrap=True, overflow="ellipsis")

        for i, s in enumerate(strategies, 1):
            table.add_row(str(i), s.name, s.description)

        console.print(table)

        # Issue #3: visually distinct hint block
        console.print()
        console.print(f" [grey62]Numbers separated by commas [bold white]1,3[/bold white]   "
                      f"All at once [bold white]a[/bold white]   "
                      f"Cancel [bold white]Enter[/bold white][/grey62]")
        console.print()

        # Issue #4: context-anchored prompt label
        raw = typer.prompt(" Install which client(s)?")
        raw = raw.strip().lower()

        # Issue #5: newline before warnings so they never share a line with the prompt
        console.print()

        if not raw:
            console.print(" [grey62]No selection — nothing installed.[/grey62]\n")
            raise typer.Exit(0)

        if raw in ("a", "all", "*"):
            selected_names = [s.name for s in strategies]
        else:
            chosen_indices: list[int] = []
            warnings: list[str] = []
            for token in raw.split(","):
                token = token.strip()
                if token.isdigit():
                    idx = int(token) - 1
                    if 0 <= idx < len(strategies):
                        chosen_indices.append(idx)
                    else:
                        warnings.append(f" [yellow]{token!r} is out of range (1–{len(strategies)})[/yellow]")
                elif token:
                    warnings.append(f" [yellow]{token!r} is not a valid number — skipped[/yellow]")

            for w in warnings:
                console.print(w)

            if not chosen_indices:
                console.print(" [yellow]No valid selection — nothing installed.[/yellow]\n")
                raise typer.Exit(0)

            selected_names = [strategies[i].name for i in chosen_indices]
    else:
        selected_names = [s.name for s in strategies]


    results = install_mcp_server("kolay-ik", cmd, args, selected=selected_names)

    success_count = 0
    for client_name, success, msg in results:
        if success:
            # Issue #6: show ~/… path instead of /Users/…
            console.print(f" [green][/green] [bold]{client_name}[/bold]: Configured.")
            console.print(f" [grey62]{_tilde(msg)}[/grey62]")
            success_count += 1
        else:
            if "Unsupported platform" in msg or "not determinable" in msg:
                console.print(f" [grey50]o[/grey50] [bold grey62]{client_name}[/bold grey62]: Skipped ({msg})")
            else:
                console.print(f" [red][/red] [bold]{client_name}[/bold]: Failed.")
                console.print(f" [red dim]{msg}[/red dim]")

    console.print()
    if success_count > 0:
        console.print(f"[green]{success_count} client(s) configured.[/green] Restart your client(s) to apply.\n")
    else:
        console.print(f"[yellow]Nothing was configured.[/yellow]")
        console.print(f" Manual config command: [bold]{cmd}[/bold]   args: {json.dumps(args)}\n")


@app.command(name="clients")
def list_clients() -> None:
    """List supported AI client integrations and their config paths.""" # Issue #8: consistent verb
    from rich.table import Table
    from ..services.mcp_registry import get_strategies

    strategies = get_strategies()

    # Issue #1: Drop the Description column — just #, Client, Config path (no wrapping)
    table = Table(
        header_style=f"bold {_PRIMARY}",
        border_style=_PRIMARY,
        box=None, show_edge=False,
    )
    table.add_column("#", style="grey62", justify="right", width=3, no_wrap=True)
    table.add_column("Client", style="bold white", min_width=22, no_wrap=True)
    table.add_column("Config path", style="grey62", no_wrap=True)

    for i, s in enumerate(strategies, 1):
        p = s.get_config_path()
        path_str = _tilde(str(p)) if p else "n/a"
        table.add_row(str(i), s.name, path_str)

    console.print(f"\n[bold {_PRIMARY}]Supported MCP Clients[/bold {_PRIMARY}] [grey62]({len(strategies)} total)[/grey62]\n")
    console.print(table)
    console.print()
