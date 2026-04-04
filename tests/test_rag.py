import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_qdrant():
    with patch("kolay_cli.rag.vector_store.QdrantClient") as MockClient:
        yield MockClient

def test_vector_store_isolation(mock_qdrant):
    from kolay_cli.rag.vector_store import get_client, search_tenant_knowledge
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    mock_instance = mock_qdrant.return_value
    mock_hit = MagicMock()
    mock_hit.score = 0.95
    mock_hit.payload = {"document_name": "test.pdf", "text": "secret rules"}
    
    # We mock search to return results
    mock_instance.search.return_value = [mock_hit]
    
    client = get_client()
    query_vector = [0.1, 0.2, 0.3]
    
    results = search_tenant_knowledge(client, tenant_id="tenant_123", query_vector=query_vector, limit=1)
    
    assert len(results) == 1
    assert results[0]["document"] == "test.pdf"
    assert results[0]["text"] == "secret rules"
    
    # Assert isolation filter was actually applied
    mock_instance.search.assert_called_once()
    kwargs = mock_instance.search.call_args.kwargs
    assert "query_filter" in kwargs
    filter_arg = kwargs["query_filter"]
    
    assert isinstance(filter_arg, Filter)
    assert len(filter_arg.must) == 1
    assert filter_arg.must[0].key == "tenant_id"
    assert filter_arg.must[0].match.value == "tenant_123"

def test_pipeline_import_safe():
    # Calling process without PDF will raise ValueError safely
    from kolay_cli.rag.pipeline import process_file_to_qdrant
    with pytest.raises(ValueError, match="only PDF"):
        process_file_to_qdrant("tenant_123", "dummy.txt")

def test_rag_tool_missing_deps():
    from kolay_cli.mcp.rag import _rag_search_corporate_memory_tool

    with patch("kolay_cli.proxy.auth.get_tenant_id", return_value="tenant_ok"):
        with patch("kolay_cli.proxy.auth.KOLAY_TOKEN_CTX") as mock_ctx:
            mock_ctx.get.return_value = "fake_token"
            with patch("kolay_cli.mcp.rag.retrieve_context", return_value=[]):
                resp = _rag_search_corporate_memory_tool(query="hello")
                assert resp["results"] == []
                assert "No relevant documents" in resp["message"]

