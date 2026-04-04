"""Vector Database Interface (Qdrant).

Manages tenant namespaces securely so no cross-tenant bleeding occurs.
We use Qdrant's payload filtering to restrict searches to a specific tenant_id.
"""
import os
from typing import List, Dict, Any, Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
except ImportError:
    pass

_COLLECTION_NAME = "kolay_tenant_kb"
_VECTOR_SIZE = 384  # fastembed bge-small default

def get_client() -> "QdrantClient":
    # Allows falling back to in-memory for testing, or connecting to a real Qdrant cluster
    url = os.environ.get("QDRANT_URL")
    api_key = os.environ.get("QDRANT_API_KEY")
    # For local server prototyping, you could save Qdrant data to disk instead of memory
    if url:
        return QdrantClient(url=url, api_key=api_key)
    path = os.environ.get("QDRANT_LOCAL_PATH", ".qdrant_data")
    return QdrantClient(path=path)

def ensure_collection(client: "QdrantClient") -> None:
    if not client.collection_exists(_COLLECTION_NAME):
        client.create_collection(
            collection_name=_COLLECTION_NAME,
            vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
        )

def upsert_chunks(client: "QdrantClient", tenant_id: str, document_name: str, chunks: List[str], embeddings: List[List[float]]) -> None:
    ensure_collection(client)
    
    import uuid
    points = []
    for chunk, vector in zip(chunks, embeddings):
        point_id = str(uuid.uuid4())
        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "tenant_id": tenant_id,
                    "document_name": document_name,
                    "text": chunk
                }
            )
        )
    
    client.upsert(
        collection_name=_COLLECTION_NAME,
        points=points
    )

def search_tenant_knowledge(client: "QdrantClient", tenant_id: str, query_vector: List[float], limit: int = 3) -> List[dict[str, Any]]:
    ensure_collection(client)
    
    # Secure tenant isolation via strict filter
    tenant_filter = Filter(
        must=[
            FieldCondition(
                key="tenant_id",
                match=MatchValue(value=tenant_id)
            )
        ]
    )
    
    results = client.search(
        collection_name=_COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=tenant_filter,
        limit=limit,
    )
    
    return [
        {
            "score": hit.score,
            "document": hit.payload.get("document_name", "unknown"),
            "text": hit.payload.get("text", "")
        }
        for hit in results
    ]
