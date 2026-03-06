"""
Schema export — ``kolay schema``

Dumps the full CLI command tree as JSON so agents can discover
available commands, arguments, and options programmatically.
"""
from __future__ import annotations

import json
import click
import typer

# Option names containing any of these strings will have their defaults omitted
# to avoid leaking sensitive values (tokens, URLs, secrets).
_SENSITIVE = frozenset({"token", "password", "secret", "key", "url"})

app = typer.Typer(
    help="Export CLI schema for agent discovery.",
    hidden=True,
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def _run_default(ctx: typer.Context) -> None:
    """Run the schema export when invoked as `kolay schema`."""
    if ctx.invoked_subcommand is None:
        export_schema()


def _opt_entry(p: click.Option) -> dict:
    """Serialise a Click option, omitting defaults for sensitive-looking names."""
    name = p.opts[0] if p.opts else (p.name or "")
    entry: dict = {"name": name, "type": p.type.name, "required": p.required}
    is_sensitive = any(s in name.lower() for s in _SENSITIVE)
    if p.default is not None and not is_sensitive:
        entry["default"] = p.default
    if p.help:
        entry["help"] = p.help
    return entry


def _walk(group: click.Group) -> dict:
    """Recursively extract commands, arguments, and options from a Click group."""
    tree: dict = {}
    for name, cmd in sorted(group.commands.items()):
        node: dict = {}
        if cmd.help:
            node["help"] = cmd.help.split("\n")[0]

        opts = [
            _opt_entry(p)
            for p in cmd.params
            if isinstance(p, click.Option) and "--help" not in p.opts
        ]
        if opts:
            node["options"] = opts

        args = [
            {"name": p.name, "required": p.required}
            for p in cmd.params
            if isinstance(p, click.Argument)
        ]
        if args:
            node["arguments"] = args

        if isinstance(cmd, click.Group):
            children = _walk(cmd)
            if children:
                node["commands"] = children

        tree[name] = node
    return tree


@app.command(name="schema")
def export_schema() -> None:
    """Dump the full CLI command tree as JSON (for agent tool discovery)."""
    from ..cli import app as root_app

    click_app = typer.main.get_command(root_app)
    tree = _walk(click_app)
    # Remove self-reference — agents don't need to discover `kolay schema` recursively
    tree.pop("schema", None)

    payload = {
        "name": "kolay",
        "version": _get_version(),
        "commands": tree,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _get_version() -> str:
    try:
        from .. import __version__
        return __version__
    except Exception:
        return "unknown"
