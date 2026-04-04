# Kolay AI Box — MCP Proxy
# Installs kolay-cli (from PyPI) + mcpo into a minimal image.
# mcpo bridges MCP stdio -> OpenAPI HTTP so Open WebUI can connect.

FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv
RUN uv pip install --system --no-cache kolay-cli mcpo

# ── Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim

# Copy everything pip/uv installed: packages, binaries, and shared libs.
# Cherry-picking site-packages + individual bins breaks when native
# extensions (pydantic-core, cryptography) link to system .so files.
COPY --from=builder /usr/local /usr/local

COPY bin/proxy-entrypoint.sh /app/proxy-entrypoint.sh
RUN chmod +x /app/proxy-entrypoint.sh

EXPOSE 8000

# No HEALTHCHECK here — compose.yml defines it using python3 (curl is
# not installed in python:3.12-slim and would always fail, blocking
# the entire startup chain via depends_on: condition: service_healthy).

CMD ["/app/proxy-entrypoint.sh"]
