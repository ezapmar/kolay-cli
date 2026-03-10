# CLAUDE.md — Claude Code directives for kolay-cli

## Rules

- Always use `--json` when reading data. Parse the JSON, never scrape Rich tables.
- Always use `--yes` on destructive commands (delete, terminate).
- Check exit codes: 0=ok, 2=bad input, 3=not found, 4=reauth needed, 5=conflict.
- If exit code 4 run `kolay auth login` before retrying.
- Never log or echo API tokens. Use `kolay config show` to verify auth state.

## Discovery

Run `kolay --help` to see all command groups.
Run `kolay <group> --help` to see subcommands and options.

## Preferred Patterns

```bash
# List and filter
kolay --json person list --search "name" --page 1 --limit 50

# Get a specific record
kolay --json person view <id>

# Create (provide all flags to skip prompts)
kolay --json leave create --person-id <id> --type annual --start 2025-03-10 --end 2025-03-11

# Delete without confirmation
kolay --yes timelog delete <id>
```

## Testing Changes

```bash
uv run --extra test pytest tests/ -v
```
