<!-- =========================================================================
     docs/BOX.md — Kolay AI Box (self-hosted interface) reference
     =========================================================================
     MAINTENANCE POLICY
     Append new Makefile targets or env vars to the relevant table.
     Do not rewrite existing sections unless a fact has changed.
     ========================================================================= -->

# Kolay AI Box

Self-hosted AI HR assistant. Runs on your own hardware.
No cloud dependency. No data leaves your network.

> **Disclaimer.** This is an independent project, not an official Kolay Yazilim A.S. product.
> All write operations target live HR data. There is no sandbox.
> You are responsible for your API token and all actions performed.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [First Boot](#first-boot)
- [Configuration](#configuration)
- [Token Modes](#token-modes)
- [Makefile Reference](#makefile-reference)
- [Architecture](#architecture)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Cloud Deployment](#cloud-deployment)
- [Uninstall](#uninstall)

---

## Overview

Kolay AI Box packages three components into a single Docker Compose stack:

| Component | Role |
|-----------|------|
| [Open WebUI](https://openwebui.com) | Chat interface (port 3000) |
| [Ollama](https://ollama.ai) | Local LLM inference (Gemma 4) |
| Kolay MCP Proxy | Connects the LLM to Kolay IK API |

The browser talks to Open WebUI. Open WebUI talks to Ollama. When the LLM needs
HR data, it calls the proxy. The proxy fetches from Kolay IK and returns JSON.
The LLM formats the response. No external AI service is involved.

---

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| Docker | 24.0+ |
| Docker Compose | v2.20+ |
| RAM | 8 GB (CPU mode), 16 GB recommended |
| Disk | 15 GB free (for model weights) |
| GPU (optional) | NVIDIA with CUDA 12+ and nvidia-container-toolkit |

### Install Docker

**macOS:**
Download [Docker Desktop](https://www.docker.com/products/docker-desktop/) and install.

**Ubuntu / Debian:**
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
# log out and back in for group change to take effect
```

**Verify:**
```bash
docker --version
docker compose version
```

### Install NVIDIA Container Toolkit (GPU mode only)

```bash
# Ubuntu / Debian
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Verify: `docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi`

---

## Installation

```bash
# clone the repository
git clone https://github.com/ezapmar/kolay-cli.git
cd kolay-cli/box

# start in CPU mode (Mac, laptop, no GPU)
make dev

# or start with GPU (NVIDIA)
make up
```

On first run, `make` creates a `.env` file from the template with generated secrets.
It prints the admin password and asks you to run the command again.

```
  Created .env with generated secrets.
    1. Optionally set KOLAY_API_TOKEN for global mode
    2. Note your admin password: <generated>

  Then run this command again.
```

Run `make dev` (or `make up`) again to start.

The first boot pulls the Gemma 4 model. This takes 5-15 minutes depending on your
connection speed. Monitor progress:

```bash
docker compose logs -f ollama
```

---

## First Boot

1. Open **http://localhost:3000** in your browser.
2. Create an account using the admin credentials from `.env`.
3. Start a chat. Ask a question about your HR data.
4. The system asks for your Kolay IK API token on first use.
5. Paste it. The token is validated and stored for your session.

That is all. No settings menus, no configuration wizards.

---

## Configuration

All configuration is in the `.env` file. Edit it and restart:

```bash
# edit
nano .env

# restart
make down && make dev
```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_MODEL` | `gemma4:26b` | LLM model to use |
| `KOLAY_API_TOKEN` | (empty) | Global token (see Token Modes below) |
| `KOLAY_SECURITY_PROFILE` | `standard` | `standard` or `enterprise` |
| `ADMIN_EMAIL` | `admin@kolay.box` | Admin account email |
| `ADMIN_PASS` | (generated) | Admin account password |
| `ADMIN_NAME` | `Admin` | Admin display name |
| `WEBUI_PORT` | `3000` | Web UI port |
| `WEBUI_SECRET_KEY` | (generated) | Session encryption key |

### Model Selection

| Model | VRAM | Use case |
|-------|------|----------|
| `gemma4:e4b` | ~6 GB | Laptop / CPU / demo |
| `gemma4:26b` | ~17 GB | Production default (MoE, fast) |
| `gemma4:31b` | ~20 GB | Maximum quality (dense) |
| `qwen2.5:32b` | ~20 GB | Fallback if Gemma tool-calling is insufficient |

---

## Token Modes

| Mode | Configuration | Use case |
|------|---------------|----------|
| Per-user (default) | Leave `KOLAY_API_TOKEN` empty | Each user pastes their own token. Isolated permissions. |
| Global | Set `KOLAY_API_TOKEN` in `.env` | Entire team shares one token. Quick setup. |

Per-user mode is recommended for production. Each user's actions are scoped
to their own Kolay IK permissions.

---

## Makefile Reference

| Command | Action |
|---------|--------|
| `make up` | Start with GPU support |
| `make dev` | Start in CPU mode (no GPU needed) |
| `make down` | Stop all containers (data preserved) |
| `make logs` | Tail all container logs |
| `make diagnose` | Run health checks and show fixes |
| `make build` | Rebuild the proxy image |
| `make clean` | Remove containers AND volumes (destructive) |
| `make cloud-up` | Provision DigitalOcean GPU droplet |
| `make cloud-down` | Destroy droplet (volume preserved) |
| `make help` | Show all available commands |

---

## Architecture

```
Browser
  |
  v
Open WebUI  (port 3000)
  |
  +--> Ollama  (Gemma 4, local inference)
  |
  +--> Kolay MCP Proxy  (Python, FastMCP)
         |
         v
       Kolay IK API  (api.kolayik.com, HTTPS)
```

All components run as Docker containers on the same network.
The proxy is the only container that makes external network requests
(to the Kolay IK API over HTTPS).

---

## Security

### Data Privacy

- All inference happens locally. No data is sent to OpenAI, Google, or any external AI service.
- Chat history is stored in a Docker volume on your machine.
- The proxy is stateless. It does not persist tokens or HR data.

### Network

- Open WebUI listens on `localhost:3000` by default. It is not exposed to the internet.
- The proxy communicates with Kolay IK over HTTPS (TLS 1.2+).
- For internet-facing deployments, place a reverse proxy (nginx, Caddy) with TLS in front.

### Credentials

- Admin credentials are generated on first boot and printed to the terminal.
- User tokens are validated against the Kolay IK API on every use.
- Set `KOLAY_SECURITY_PROFILE=enterprise` for PII masking and DLP scanning.

### Recommended Hardening

- Change `ADMIN_PASS` and `WEBUI_SECRET_KEY` from their generated values.
- In production, bind Open WebUI to `127.0.0.1:3000` and use a TLS reverse proxy.
- Use per-user token mode to isolate permissions.
- Rotate tokens regularly.

---

## Troubleshooting

### Run diagnostics

```bash
make diagnose
```

This checks container health, port availability, GPU detection, model download
status, and API connectivity. It prints specific fixes for each problem found.

### Containers not starting

```bash
# check container status
docker compose ps

# check logs
docker compose logs -f
```

### Model download stuck or slow

```bash
# check Ollama progress
docker compose logs -f ollama
```

The Gemma 4 26b model is approximately 17 GB. On slow connections, use the
smaller model:
```bash
# in .env
OLLAMA_MODEL=gemma4:e4b
```

### "Connection refused" on localhost:3000

Wait 30-60 seconds after starting. Open WebUI needs time to initialize.
If it still fails:
```bash
docker compose ps | grep webui
```

If the container is not running, check logs:
```bash
docker compose logs webui
```

### GPU not detected

```bash
# verify NVIDIA driver
nvidia-smi

# verify container toolkit
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

If GPU is not available, use CPU mode:
```bash
make dev
```

### "Out of memory" errors

Reduce model size in `.env`:
```bash
OLLAMA_MODEL=gemma4:e4b    # smallest, ~6 GB
```

### Proxy cannot reach Kolay IK API

```bash
# test from inside the container
docker compose exec proxy curl -s https://api.kolayik.com/health
```

If this fails, check your network configuration. If you are behind a corporate
proxy, set `HTTPS_PROXY` in `.env`.

### Reset everything

```bash
make clean    # WARNING: deletes all data, models, and user accounts
```

---

## Cloud Deployment

### DigitalOcean (one-click GPU)

```bash
# provision a GPU droplet with attached volume
make cloud-up

# when done, destroy the droplet (volume preserved, billing stops)
make cloud-down
```

The scripts handle droplet creation, volume attachment, Docker installation,
and stack deployment.

### Other Cloud Providers

1. Provision a VM with Docker and (optionally) GPU support.
2. Clone the repository and `cd box`.
3. Run `make up` (GPU) or `make dev` (CPU).
4. Configure a firewall to allow port 3000 (or use a reverse proxy).

---

## Uninstall

```bash
# stop containers and remove volumes
make clean

# remove the repository
cd ../..
rm -rf kolay-cli
```

Docker images can be removed with:
```bash
docker image prune -a
```

---

## License

MIT
