# Kolay AI Box

Self-hosted AI HR assistant. Powered by Gemma 3.
Zero cloud. Total privacy. Your data stays on your machine.

## Quick Start

```bash
cd box
make dev          # CPU mode for your Mac. No GPU needed.
# or
make up           # GPU mode for the cloud. Full throttle.
```

The first run creates `.env`. Edit it. Run it again.

## Onboarding

Open **http://localhost:3000**. Create an account. Chat.
Ask a question. It asks for your Kolay IK token.
Paste it. It locks it in. You are ready.

No messy settings. No IT help. Just answers.

## Token Modes

| Mode | How it works | When to use |
|------|--------------|-------------|
| Per-user | Leave `KOLAY_API_TOKEN` empty in `.env`. | Users use own tokens. Safe. Isolated. |
| Global | Set `KOLAY_API_TOKEN` in `.env`. | Entire team shares one token. Quick. |

## The Power of Charts

It answers. It draws. Bar charts. Heatmaps. Org structures.
The AI builds HTML. Chart.js and ECharts do the heavy lifting. All local. 

```
"Who is on leave this week?"
"Show headcount by department as a pie chart."
"Draw the engineering org chart."
```

## Commands

```
/token <token>    Set a new Kolay IK token. Move on.
```

## Makefile

| Command | Action |
|---------|--------|
| `make up` | Start with GPU. |
| `make dev` | Start in CPU mode. |
| `make down` | Stop everything. Data endures. |
| `make diagnose` | Find the problem. Fix the problem. |
| `make build` | Rebuild images. |
| `make cloud-up` | Spin up a droplet. |
| `make cloud-down` | Tear it down. Stop paying. |

## Architecture

The browser hits Open WebUI.
Open WebUI talks to Ollama. Gemma 3 thinks.
To get facts, Open WebUI asks the proxy.
The proxy fetches from Kolay IK. Returns pure JSON.
The AI paints the picture.

No OpenAI. No leaks.

## Troubleshoot

```bash
make diagnose
```
It runs checks. It tells you the exact fix. Do it.
