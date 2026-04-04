"""Document pipeline for Corporate Memory.

Handles parsing PDFs, chunking text, generating embeddings, and storing them.
Delegates to vector_store for the storage layer.
"""
import os
from typing import List
import logging

_log = logging.getLogger(__name__)

try:
    from pypdf import PdfReader
    from fastembed import TextEmbedding
except ImportError as exc:
    _log.debug(f"Optional RAG dependencies missing: {exc}")

# Initialize singleton for fastembed to avoid reloading weights
_embedding_model = None

def get_embedding_model() -> "TextEmbedding":
    global _embedding_model
    if _embedding_model is None:
        # bge-small is fast, performs well, and yields dim=384 embeddings. Use multilingual mostly.
        # "intfloat/multilingual-e5-small" is good for Turkish. "BAAI/bge-m3" is heavy.
        # Let's use the default "BAAI/bge-small-en-v1.5" or small multilingual if available.
        from fastembed import TextEmbedding
        model_name = os.environ.get("FASTEMBED_MODEL", "intfloat/multilingual-e5-small")
        _embedding_model = TextEmbedding(model_name=model_name)
    return _embedding_model

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a given PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Naive text chunking by characters."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # If not at the end of the text, try to find a natural break (newline or space)
        if end < len(text):
            break_pos = text.rfind("\n", start, end)
            if break_pos == -1:
                break_pos = text.rfind(". ", start, end)
            if break_pos == -1:
                break_pos = text.rfind(" ", start, end)
                
            if break_pos > start + chunk_size // 2:
                end = break_pos + 1

        chunks.append(text[start:end].strip())
        start = end - overlap
        
    return [c for c in chunks if len(c) > 10]

def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed chunks using FastEmbed."""
    model = get_embedding_model()
    # fastembed returns a generator of numpy arrays
    embeddings_gen = model.embed(texts)
    return [emb.tolist() for emb in embeddings_gen]

def process_file_to_qdrant(tenant_id: str, file_path: str) -> int:
    """Process a PDF and load it into Qdrant. Returns the number of chunks."""
    if not file_path.endswith(".pdf"):
        raise ValueError("Currently only PDF files are supported.")
        
    text = extract_text_from_pdf(file_path)
    chunks = chunk_text(text)
    
    if not chunks:
        return 0
        
    embeddings = embed_texts(chunks)
    
    from .vector_store import get_client, upsert_chunks
    client = get_client()
    document_name = os.path.basename(file_path)
    upsert_chunks(client, tenant_id, document_name, chunks, embeddings)
    
    return len(chunks)

def query_tenant_knowledge(tenant_id: str, query: str, limit: int = 3) -> List[dict]:
    """Search tenant namespace for the given query."""
    model = get_embedding_model()
    query_vector = list(model.embed([query]))[0].tolist()
    
    from .vector_store import get_client, search_tenant_knowledge
    client = get_client()
    return search_tenant_knowledge(client, tenant_id, query_vector, limit=limit)
