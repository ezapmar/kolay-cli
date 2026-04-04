# Kolay AI Box — MCP Proxy
# Installs kolay-cli (from PyPI) + mcpo into a minimal image.
# mcpo bridges MCP stdio → OpenAPI HTTP so Open WebUI can connect.

FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv
RUN uv pip install --system --no-cache kolay-cli mcpo

# ── Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/kolay-mcp /usr/local/bin/
COPY --from=builder /usr/local/bin/mcpo /usr/local/bin/

COPY config/mcpo.json /app/mcpo.json

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD curl -sf http://localhost:8000/docs || exit 1

CMD ["mcpo", "--config", "/app/mcpo.json", "--port", "8000"]
