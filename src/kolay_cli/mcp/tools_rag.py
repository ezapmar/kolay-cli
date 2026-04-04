"""RAG corporate memory tools for MCP."""
from typing import List, Dict, Any
from .adapter import Tool
from ..proxy.auth import require_auth
from ..security import KOLAY_TOKEN_CTX
from ..proxy.auth import get_tenant_id

@require_auth
def rag_search_corporate_memory(query: str, limit: int = 3) -> Dict[str, Any]:
    """Retrieve highly relevant corporate memory context for arbitrary questions.
    Search the company's internal knowledge base and policies (RAG).
    Use this tool when employees ask about company rules, remote work policies,
    benefits, processes, or internal documentation.
    """
    token = KOLAY_TOKEN_CTX.get()
    tenant_id = get_tenant_id(token)
    
    try:
        from ..rag.pipeline import query_tenant_knowledge
    except ImportError as exc:
        return {
            "error": "RAG dependencies not installed. Admin must run: uv pip install -e \".[rag]\"",
            "detail": str(exc),
            "results": []
        }
        
    try:
        results = query_tenant_knowledge(tenant_id, query, limit=limit)
        return {
            "query": query,
            "results": results,
            "tenant_id": tenant_id
        }
    except Exception as exc:
        return {
            "error": "Internal RAG lookup failed.",
            "detail": str(exc),
            "results": []
        }

def register(mcp):
    mcp.add_tool(Tool.from_function(
        rag_search_corporate_memory, 
        annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read", "rag"}
    ))

