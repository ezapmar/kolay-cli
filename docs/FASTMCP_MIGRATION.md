# FastMCP Migration & Maintenance Guide

This document provides a technical overview of the FastMCP middleware architecture and a checklist for maintaining security layers during future FastMCP core upgrades.

## Architecture: The Adapter Pattern

We use `kolay_cli.mcp.adapter` as a shim layer. This isolates the core business logic from breaking changes in the `fastmcp` library. 

**STRICT RULE:** Never import `fastmcp.Middleware` or `fastmcp.Context` directly in tool modules. Always use the adapter.

## Middleware Stack Structure

The stack in `mcp_server.py` follows a "Russian Doll" wrapping model. The first middleware added is the **outermost** layer.

| Layer | Responsibility | Position |
|---|---|---|
| `ErrorHandlingMiddleware` | Catch-all for internal leaks | Outermost |
| `RBACToolFilterMiddleware` | **(NEW)** JIT schema filtering | Layer 2 |
| `SlidingWindowRateLimitingMiddleware` | DOS protection | Layer 3 |
| `TimingMiddleware` | Performance logging | Layer 4 |
| `ResponseLimitingMiddleware` | Context window safety | Inner |
| `PIIMaskingMiddleware` | Data privacy | Inner |

## Upgrade Checklist

When upgrading the `fastmcp` dependency, verify the following signatures haven't changed:

### 1. Middleware Interface
Ensure the `__call__` signature still accepts `(ctx: MiddlewareContext, next_call: CallNext)`.
File: [adapter.py](file:///Users/tuncaucer/projects/kolay-cli/src/kolay_cli/mcp/adapter.py)

### 2. Tool Metadata
Verify that `list_tools` still returns a list of objects containing `.name` and `.tags`.
File: [rbac.py](file:///Users/tuncaucer/projects/kolay-cli/src/kolay_cli/proxy/rbac.py)

### 3. Context State
Ensure `ctx.set_state` and `ctx.get_state` are still the standard for session memory.
File: [tools_session.py](file:///Users/tuncaucer/projects/kolay-cli/src/kolay_cli/mcp/tools_session.py)

## Verification after Upgrade

Run the standard regression suite:

```bash
uv run --extra test pytest tests/test_rbac.py tests/test_semantic_cache.py tests/test_webhook.py -v
```

If these three specific tests pass, the middleware interception logic is intact.
