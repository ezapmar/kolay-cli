"""PII Masking and Pseudonymization Layer for Kolay IK MCP Server."""
from __future__ import annotations

import collections
import hashlib
import hmac
import json
import os
import secrets
from typing import Any

from kolay_cli.mcp.adapter import TextContent

os.environ.setdefault("FASTMCP_LOG_LEVEL", "WARNING")

from kolay_cli.mcp.adapter import ToolResult, Middleware, MiddlewareContext, CallNext


# The session salt is regenerated every time the server starts.
# It ensures that pseudonym mapping (EMP-8F92) is consistent within the same session
# so the LLM can correlate identities, but changes between server restarts for privacy.
_SESSION_SALT = secrets.token_bytes(32)


# Fields targeted for deterministic hashing (pseudonymization)
_HASH_FIELDS = {"firstName", "lastName", "name", "personName"}

# Fields targeted for email masking (user-XXXX@masked.local)
_EMAIL_FIELDS = {"email", "workEmail", "personalEmail"}

# Fields targeted for static masking (***-MASKED)
_STATIC_FIELDS = {"mobilePhone", "phone", "nationalId", "identityNumber", "tckn"}

# Fields targeted for amount bucketing to the nearest integer ranges
_AMOUNT_FIELDS = {"amount", "totalAmount", "gross", "net", "salary"}



def _is_amount_masking_enabled() -> bool:
    """Return True if financial amount masking is enabled."""
    return os.environ.get("MCP_PII_MASK_AMOUNTS", "false").lower() in ("1", "true", "yes")


def _get_custom_fields() -> set[str]:
    """Parse MCP_PII_MASK_FIELDS if provided."""
    raw = os.environ.get("MCP_PII_MASK_FIELDS", "")
    if not raw:
        return set()
    return {p.strip() for p in raw.split(",") if p.strip()}


def generate_pseudonym(value: Any, prefix: str = "EMP-") -> str:
    """Generate a deterministic 4-character hex pseudonym for a given value."""
    if not value:
        return f"{prefix}NONE"
    
    val_str = str(value).strip().lower()
    h = hmac.new(_SESSION_SALT, val_str.encode("utf-8"), hashlib.sha256).hexdigest()
    # Take first 4 characters for a short, readable pseudonym
    return f"{prefix}{h[:4].upper()}"


def _mask_amount(amount: float | int) -> str:
    """Bucket a financial amount to nearest integer limits."""
    try:
        val = float(amount)
        if val <= 0:
            return "0"
        
        # Round logic (e.g. 15250 -> 15000-16000)
        import math
        magnitude = 10 ** (max(0, math.floor(math.log10(val))))
        
        factor = magnitude / 10 if magnitude >= 1000 else 100
        factor = max(100, factor)

        lower = math.floor(val / factor) * factor
        upper = lower + factor
        return f"{int(lower)}-{int(upper)}"
    except (ValueError, TypeError):
        return "***MASKED***"


def mask_value(field_name: str, value: Any, lookup: dict[str, str]) -> Any:
    """Apply the correct masking strategy based on the field name."""
    # Don't mask empty/boolean/null values
    if value is None or isinstance(value, bool) or value == "":
        return value

    custom_fields = _get_custom_fields()
    if field_name in custom_fields:
        return "***MASKED***"

    if field_name in _STATIC_FIELDS:
        return "***MASKED***"

    if field_name in _EMAIL_FIELDS:
        pseudo = generate_pseudonym(value, prefix="user-")
        result = f"{pseudo}@masked.local"
        lookup[result] = f"Masked from {field_name}"
        return result

    if field_name in _HASH_FIELDS:
        pseudo = generate_pseudonym(value, prefix="EMP-")
        lookup[pseudo] = f"Masked from {field_name}"
        return pseudo

    if field_name in _AMOUNT_FIELDS and _is_amount_masking_enabled():
        return _mask_amount(value)

    return value


def mask_dict(data: Any, lookup: dict[str, str] | None = None) -> Any:
    """Recursively walk a data structure and mask specific fields."""
    if lookup is None:
        lookup = {}
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                result[k] = mask_dict(v, lookup)
            else:
                result[k] = mask_value(k, v, lookup)
        return result
    elif isinstance(data, list):
        return [mask_dict(item, lookup) for item in data]
    else:
        return data


class PIIMaskingMiddleware(Middleware):
    """FastMCP middleware to intercept and mask PII in tool responses."""

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: CallNext,
    ) -> ToolResult:
        """Process tool call and parse the outgoing response."""
        result = await call_next(context)

        if not result or not result.content:
            return result

        # Per-call lookup dict — no shared state across concurrent requests
        lookup: dict[str, str] = {}

        new_contents = []

        for block in result.content:
            if isinstance(block, TextContent):
                # Try to parse the text as JSON, usually returned by the MCP wrapper
                try:
                    data = json.loads(block.text)
                    masked_data = mask_dict(data, lookup)

                    # Only append lookup table if we actually masked something
                    if lookup:
                        if isinstance(masked_data, dict):
                            masked_data["_pii_lookup"] = dict(lookup)

                    new_text = json.dumps(masked_data, ensure_ascii=False, default=str)
                    new_contents.append(TextContent(type="text", text=new_text))
                except (json.JSONDecodeError, TypeError):
                    # If it's not JSON, leave as-is
                    new_contents.append(block)
            else:
                new_contents.append(block)

        result.content = new_contents
        return result

