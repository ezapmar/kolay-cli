# ── Kolay AI Box ─────────────────────────────────────────────────────
# Plug-and-play commands. No need to remember docker flags.
#
# Quick start:
#   make up         Start the stack (GPU required)
#   make dev        Start in CPU mode (laptop, no GPU)
#   make down       Stop everything
#   make diagnose   Check what's working and what's not
#
# Cloud (DigitalOcean):
#   make cloud-up   Provision GPU droplet + volume
#   make cloud-down Destroy droplet (volume preserved, billing stops)
# ─────────────────────────────────────────────────────────────────────

.DEFAULT_GOAL := help

# ── Local ────────────────────────────────────────────────────────────

.PHONY: up
up: _ensure-env ## Start the stack with GPU (requires NVIDIA)
	docker compose -f compose.yml -f compose.gpu.yml up -d
	@echo ""
	@echo "  Kolay AI Box is starting (GPU mode)."
	@echo "  First boot pulls the model — this can take a few minutes."
	@echo "  Monitor: docker compose logs -f ollama"
	@echo ""
	@echo "  Once ready, open: http://localhost:$${WEBUI_PORT:-3000}"
	@echo ""

.PHONY: dev
dev: _ensure-env ## Start in CPU mode (no GPU required, works on Mac)
	docker compose -f compose.yml -f compose.cpu.yml up -d
	@echo ""
	@echo "  Kolay AI Box (CPU mode) is starting."
	@echo "  Tip: Set OLLAMA_MODEL=gemma4:e4b in .env for fastest CPU inference."
	@echo ""
	@echo "  Once ready, open: http://localhost:$${WEBUI_PORT:-3000}"
	@echo ""

.PHONY: down
down: ## Stop all containers
	@docker compose -f compose.yml -f compose.gpu.yml down 2>/dev/null || \
		docker compose -f compose.yml down
	@echo "  Stopped. Data is preserved in Docker volumes."

.PHONY: logs
logs: ## Tail all container logs
	docker compose -f compose.yml logs -f

.PHONY: diagnose
diagnose: ## Run health checks (find and fix problems)
	@bash bin/diagnose.sh

.PHONY: build
build: ## Rebuild the proxy image (run after kolay-cli updates)
	docker compose -f compose.yml build proxy

.PHONY: clean
clean: ## Remove all containers AND volumes (destructive!)
	@echo "  This will DELETE all chat history, model weights, and user accounts."
	@read -p "  Are you sure? [y/N] " ans && [ "$$ans" = "y" ] || exit 1
	docker compose -f compose.yml down -v
	@echo "  Cleaned."

# ── Cloud (DigitalOcean) ────────────────────────────────────────────

.PHONY: cloud-up
cloud-up: ## Provision DO GPU droplet + attach volume
	@bash bin/deploy.sh

.PHONY: cloud-down
cloud-down: ## Destroy droplet (volume preserved, billing stops)
	@bash bin/teardown.sh

# ── Internal ─────────────────────────────────────────────────────────

.PHONY: _ensure-env
_ensure-env:
	@if [ ! -f .env ]; then \
		echo ""; \
		echo "  .env not found. Creating from template..."; \
		cp .env.example .env; \
		SECRET_KEY=$$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))"); \
		ADMIN_PW=$$(openssl rand -base64 18 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(18))"); \
		sed -i.bak "s/change-me-to-a-long-random-string/$$SECRET_KEY/" .env; \
		sed -i.bak "s/change-me-min-8-chars/$$ADMIN_PW/" .env; \
		rm -f .env.bak; \
		echo "  Created .env with generated secrets."; \
		echo "    1. Optionally set KOLAY_API_TOKEN for global mode"; \
		echo "    2. Note your admin password: $$ADMIN_PW"; \
		echo ""; \
		echo "  Then run this command again."; \
		exit 1; \
	fi

.PHONY: help
help: ## Show this help
	@echo ""
	@echo "  Kolay AI Box — Self-hosted AI HR Assistant"
	@echo ""
	@echo "  Usage: make <command>"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-14s\033[0m %s\n", $$1, $$2}'
	@echo ""
