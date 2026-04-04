"""Layer 2 RAG Integration — Secure Corporate Memory context injection.

This module is the bridge between Layer 2 (vector DB retrieval) and Layer 3
(MCP tool responses). It provides:

  1. RAG context retrieval scoped strictly to the caller's tenant_id.
  2. A context-injection helper that LLM-facing tool responses can call to
     prepend relevant corporate knowledge before returning HR data.
  3. The standalone MCP tool `rag_search_corporate_memory` for direct queries.

Architecture (§5.2 / §7.3):
    LLM query → Gateway → rag.retrieve_context(tenant_id, query)
                         → Qdrant (tenant-scoped filter)
                         → top-k chunks prepended to tool response
                         → LLM sees: [policy context] + [HR data]
"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API — used by tools that want RAG context enrichment
# ---------------------------------------------------------------------------

def retrieve_context(tenant_id: str, query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Return top-k relevant corporate knowledge chunks for the given query.

    Returns an empty list if:
    - RAG dependencies are not installed (`[rag]` extra)
    - Qdrant is unreachable
    - No documents have been ingested for this tenant

    Never raises — RAG is best-effort enrichment. Core HR tools must work
    even when the vector DB is unavailable.
    """
    try:
        from ..rag.pipeline import query_tenant_knowledge
        return query_tenant_knowledge(tenant_id, query, limit=limit)
    except ImportError:
        _log.debug("RAG dependencies not installed; context retrieval skipped.")
        return []
    except Exception as exc:
        _log.warning("RAG retrieval failed for tenant %s: %s", tenant_id, exc)
        return []


def inject_rag_context(
    response: dict[str, Any],
    tenant_id: str,
    query: str,
    context_key: str = "_corporate_context",
) -> dict[str, Any]:
    """Enrich a tool response dict with RAG context chunks.

    Mutates and returns the response with a `_corporate_context` key added
    when relevant chunks are found. The LLM is expected to read this context
    before composing its final answer.

    This is intentionally lightweight — it does NOT rewrite the response or
    call an LLM. It surfaces the raw chunks so the *calling* LLM can synthesize.

    Args:
        response: The existing tool response dict.
        tenant_id: Tenant namespace to scope the Qdrant query.
        query: The user's original question (used for semantic search).
        context_key: Key to inject under in the response dict.

    Returns:
        The enriched response dict (same object, modified in place).
    """
    chunks = retrieve_context(tenant_id, query, limit=3)
    if not chunks:
        return response

    # Summarise chunks for context window efficiency
    context_snippets = [
        {
            "source": c.get("document", "unknown"),
            "relevance": round(c.get("score", 0.0), 3),
            "excerpt": c.get("text", "")[:500],  # Hard-cap each chunk at 500 chars
        }
        for c in chunks
        if c.get("score", 0.0) >= 0.4  # Discard low-relevance noise
    ]

    if context_snippets:
        response[context_key] = {
            "note": (
                "The following excerpts are from your company's internal knowledge base. "
                "Use them to supplement the HR data above when answering the user's question."
            ),
            "chunks": context_snippets,
        }

    return response


# ---------------------------------------------------------------------------
# FastMCP tool: rag_search_corporate_memory (direct query, no HR data join)
# ---------------------------------------------------------------------------

def _rag_search_corporate_memory_tool(query: str, limit: int = 3) -> dict[str, Any]:
    """[READ] Search the company's internal knowledge base and policies.

    Use this when the user asks about company rules, remote work policies,
    benefits, processes, or internal documentation that is NOT stored in
    Kolay IK as structured HR data.

    Examples:
      - \"What is our policy on remote work?\"
      - \"How do I submit an expense claim?\"
      - \"What are the rules for overtime in our company?\"

    Returns: top matching excerpts with relevance scores and source documents.
    """
    from ..proxy.auth import require_auth, get_tenant_id
    from ..security import KOLAY_TOKEN_CTX

    token = KOLAY_TOKEN_CTX.get()
    tenant_id = get_tenant_id(token)

    chunks = retrieve_context(tenant_id, query, limit=limit)

    if not chunks:
        return {
            "query": query,
            "tenant_id": tenant_id,
            "results": [],
            "message": (
                "No relevant documents found. "
                "Ask your admin to ingest company documents with: "
                "kolay rag ingest <tenant_id> <document.pdf>"
            ),
        }

    return {
        "query": query,
        "tenant_id": tenant_id,
        "results": [
            {
                "document": c.get("document", "unknown"),
                "score": round(c.get("score", 0.0), 3),
                "excerpt": c.get("text", ""),
            }
            for c in chunks
        ],
    }


def register(mcp: Any) -> None:
    """Register RAG tools with the FastMCP server."""
    from ..proxy.auth import require_auth
    from .adapter import Tool

    # Wrap the tool function with auth
    authed_fn = require_auth(_rag_search_corporate_memory_tool)
    # Copy over the docstring so FastMCP picks it up as the tool description
    authed_fn.__doc__ = _rag_search_corporate_memory_tool.__doc__
    authed_fn.__name__ = "rag_search_corporate_memory"

    mcp.add_tool(Tool.from_function(
        authed_fn,
        annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read", "rag"},
    ))
