"""Schema export commands."""
from __future__ import annotations

import json
import typer
from rich.console import Console

app = typer.Typer(help="Export OpenAPI schemas for the Kolay IK MCP tools.")
console = Console(highlight=False)


@app.command(name="export")
def export(
    format: str = typer.Option(
        "openapi",
        "--format", "-f",
        help="Export format (only 'openapi' is currently supported).",
    )
) -> None:
    """Generate and print an OpenAPI specification from the MCP tool registry."""
    if format.lower() != "openapi":
        console.print(f"[bold red]Unsupported format '[/bold red]{format}[bold red]'.[/bold red] Use 'openapi'.")
        raise typer.Exit(1)

    import asyncio
    try:
        from ..mcp_server import mcp
    except ImportError:
        console.print("\n[bold red]fastmcp is not installed.[/bold red]\n")
        raise typer.Exit(1)

    tools = asyncio.run(mcp.list_tools())
    
    # OpenAPI shell
    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "Kolay IK MCP API",
            "version": "1.0.0",
            "description": "Auto-generated OpenAPI schema from Kolay IK FastMCP tools.",
        },
        "servers": [
            {
                "url": "http://localhost:8080/mcp",
                "description": "Local / proxy MCP Server HTTP endpoint"
            }
        ],
        "paths": {},
        "components": {
            "schemas": {}
        }
    }

    for tool in tools:
        is_write = any(w in tool.name.lower() for w in ("create", "update", "delete", "terminate", "rehire", "manage", "assign"))
        method = "post" if is_write else "get"
        path = f"/tools/{tool.name}"

        operation = {
            "summary": tool.name,
            "description": getattr(tool, "description", ""),
            "operationId": tool.name,
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {}
                    }
                }
            }
        }

        # Handle parameters
        if getattr(tool, "parameters", None) and tool.parameters.get("properties"):
            schema_name = f"{tool.name.capitalize()}Input"
            spec["components"]["schemas"][schema_name] = tool.parameters
            
            if method == "post":
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": f"#/components/schemas/{schema_name}"
                            }
                        }
                    }
                }
            else:
                parameters = []
                for prop_name, prop_schema in tool.parameters.get("properties", {}).items():
                    parameters.append({
                        "name": prop_name,
                        "in": "query",
                        "required": prop_name in tool.parameters.get("required", []),
                        "schema": prop_schema,
                    })
                operation["parameters"] = parameters

        spec["paths"][path] = {
            method: operation
        }

    # Use standard print to allow piping to file without rich formatting
    print(json.dumps(spec, indent=2))
