# kolay-cli

An unofficial command-line interface and MCP server for Kolay İK.

## Notice

This is an unofficial lab project. It is not an official product of Kolay Yazılım A.Ş. They are not responsible for data loss or system errors. You are responsible for your API tokens. Use the tools with care. They change live data.

## Install

Install via standalone wizard:
1. Download the [latest release](https://github.com/ezapmar/kolay-cli/releases).
2. Run `kolay-setup`.
3. Accept the disclaimer and follow the prompts.

Or install via pip:
```bash
pipx install kolay-cli
kolay setup
```

## Example

```bash
kolay person list
kolay leave create --type annual --start 2026-03-01 --end 2026-03-03
```

## Commands

Commands follow the `kolay <resource> <action>` pattern.

| Resource | Action |
|---|---|
| auth | login, logout, status |
| config | show, set |
| person | list, view, summary, create, update, terminate |
| leave | list, create |
| timelog | list, create, delete |
| training | list, create, delete |
| calendar | list, create, update, delete |
| unit | tree |
| doctor | health check |

## MCP Server

Integrate Kolay İK with AI assistants.

```bash
kolay mcp install
```

## Output Modes

* `--json`: Machine-readable output.
* `--yes`: Bypass confirmations.
* `--debug`: Write HTTP traces to `~/.config/kolay/debug.log`.

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Error |
| 2 | Bad input |
| 3 | Not found |
| 4 | Auth error |
| 5 | Conflict |

## Links

* [API Docs](https://apidocs.kolayik.com)
* [GitHub](https://github.com/ezapmar/kolay-cli)
