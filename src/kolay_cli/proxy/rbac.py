"""JIT Role-Based Access Control for MCP tools.

Enforces tool visibility and execution-level security based on user roles
extracted from JWT claims. Reduces token usage and prompt injection surface.

Roles:
- employee: Read-only access to self-service tools.
- hr_manager: Read/Write/Analytics access (excluding destructive/admin).
- hr_admin: Unrestricted access.
"""
from __future__ import annotations

import logging
from typing import Any, Coroutine

from ..security import KOLAY_TOKEN_CTX
from ..mcp.adapter import Middleware, MiddlewareContext, CallNext

_log = logging.getLogger(__name__)

# --- Role Policy ---

# Roles allowed to see/execute specific tool tags.
# Tags are defined in tool registration (e.g. tools_people.py).
ROLE_TAG_ALLOWLIST = {
    "employee": frozenset({"read", "session", "diagnostic"}),
    "hr_manager": frozenset({
        "read", "write", "session", "diagnostic", "analytics", "wellness", "smart_proxy"
    }),
    "hr_admin": frozenset({
        # hr_admin gets everything by logic, but these are explicit
        "read", "write", "destructive", "admin", "session", "diagnostic", 
        "analytics", "wellness", "smart_proxy"
    }),
}

DEFAULT_ROLE = "employee"


def resolve_user_role() -> str:
    """Extract user_role from JWT claims in the current context.
    
    Checks 'user_role', 'role', or 'roles' claims.
    Falls back to 'employee' if no JWT or no known role found.
    """
    token = KOLAY_TOKEN_CTX.get()
    if not token:
        return DEFAULT_ROLE

    # Basic JWT decoding (extracting claims without full signature validation again
    # as that was already handled by APIKeyMiddleware/require_auth).
    try:
        from .auth import _decode_jwt_claims
        claims = _decode_jwt_claims(token)
        if not claims:
            return DEFAULT_ROLE
        
        # Check claims in order of specificity
        raw_role = claims.get("user_role") or claims.get("role") or claims.get("roles")
        if isinstance(raw_role, list) and raw_role:
            raw_role = raw_role[0]
        
        role = str(raw_role).lower() if raw_role else DEFAULT_ROLE
        return role if role in ROLE_TAG_ALLOWLIST else DEFAULT_ROLE
    except Exception:
        # Fallback for opaque tokens or decoding errors
        return DEFAULT_ROLE


def is_tool_allowed(tool_tags: set[str], role: str) -> bool:
    """Return True if the role is authorized for the given tool tags."""
    if role == "hr_admin":
        return True
    
    allowed_tags = ROLE_TAG_ALLOWLIST.get(role, ROLE_TAG_ALLOWLIST[DEFAULT_ROLE])
    # Tool is allowed if all its tags are in the allowlist OR it has no tags (public)
    if not tool_tags:
        return True
        
    return any(tag in allowed_tags for tag in tool_tags)


class RBACToolFilterMiddleware(Middleware):
    """FastMCP middleware for JIT tool provisioning and RBAC enforcement.
    
    1. Intercepts list_tools: filters the results based on user role.
    2. Intercepts call_tool: prevents execution of unauthorized tools (403).
    """

    async def __call__(
        self,
        ctx: MiddlewareContext,
        next_call: CallNext,
    ) -> Any:
        role = resolve_user_role()
        
        # --- Handle list_tools ---
        if ctx.operation == "list_tools":
            result = await next_call(ctx)
            # result is list[Tool] from FastMCP
            if not isinstance(result, list):
                return result
                
            filtered = []
            for tool in result:
                # FastMCP Tool objects have .tags (set)
                tags = getattr(tool, "tags", set())
                if is_tool_allowed(tags, role):
                    filtered.append(tool)
                else:
                    _log.debug("RBAC: Filtering out tool '%s' for role '%s'", tool.name, role)
            return filtered

        # --- Handle call_tool ---
        if ctx.operation == "call_tool":
            tool_name = ctx.request.params.get("name")
            # We need to find the tool definition to check its tags.
            # FastMCP server has a .tools dict.
            mcp_server = getattr(ctx, "server", None)
            if mcp_server and hasattr(mcp_server, "tools"):
                tool = mcp_server.tools.get(tool_name)
                if tool:
                    tags = getattr(tool, "tags", set())
                    if not is_tool_allowed(tags, role):
                        _log.warning("RBAC 403: Role '%s' denied access to tool '%s'", role, tool_name)
                        return {
                            "error": True,
                            "code": 403,
                            "message": f"Access denied. Tool '{tool_name}' is not available for your role ('{role}').",
                            "hint": "Contact your administrator to upgrade your access level.",
                            "exit_code": 4, # Auth/Permission denied
                        }

        return await next_call(ctx)
