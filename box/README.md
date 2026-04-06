# Kolay AI Box

Self-hosted AI HR assistant. Powered by Gemma 4.
Zero cloud. Total privacy. Your data stays on your machine.

> Full documentation: [docs/BOX.md](../docs/BOX.md)

## Quick Start

```bash
cd box
make dev          # CPU mode, no GPU needed
# or
make up           # GPU mode (NVIDIA)
```

On first run, `.env` is created from the template with generated secrets.
Run the command again to start.

Open **http://localhost:3000**. Create an account. Chat.

## Commands

| Command | Action |
|---------|--------|
| `make up` | Start with GPU |
| `make dev` | Start in CPU mode |
| `make down` | Stop everything (data preserved) |
| `make diagnose` | Run health checks |
| `make logs` | Tail logs |
| `make clean` | Remove all data (destructive) |

## Troubleshooting

```bash
make diagnose
```

See [docs/BOX.md](../docs/BOX.md) for detailed setup, configuration, and troubleshooting.
