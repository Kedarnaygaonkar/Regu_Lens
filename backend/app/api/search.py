"""
Search API routes.
POST /search — Hybrid retrieval
GET  /chunks/{id} — Chunk detail
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
import time

from app.config import get_settings
from app.database import Collections, get_sync_db
from app.embeddings import get_embedding_provider
from app.models.query import QueryRequest, SearchResponse
from app.retrieval.hybrid_retriever import hybrid_retrieve

router = APIRouter(tags=["Search"])


def _get_embedding_provider():
    settings = get_settings()
    try:
        return get_embedding_provider(
            provider=settings.embedding_provider,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
        )
    except Exception:
        return None


@router.post("/search", summary="Hybrid search (vector + keyword)")
def search(request: QueryRequest):
    """
    Perform hybrid retrieval across all ingested documents.
    Returns ranked chunks with full provenance.
    """
    start = time.time()

    query_embedding = []
    emb_provider = _get_embedding_provider()
    if emb_provider and request.use_hybrid:
        try:
            query_embedding = emb_provider.embed_query(request.query)
        except Exception as e:
            pass  # Fall back to keyword-only

    results = hybrid_retrieve(
        query=request.query,
        query_embedding=query_embedding,
        top_k=request.top_k,
        filters=request.filters or {},
        include_superseded=request.include_superseded,
        use_vector=bool(query_embedding),
        use_keyword=True,
    )

    elapsed = (time.time() - start) * 1000

    return SearchResponse(
        query=request.query,
        results=results,
        total=len(results),
        latency_ms=elapsed,
    )


@router.get("/chunks/{chunk_id}", summary="Get chunk details")
def get_chunk(chunk_id: str):
    """Get a specific chunk by ID (without embedding vector)."""
    db = get_sync_db()
    chunk = db[Collections.CHUNKS].find_one({"chunk_id": chunk_id}, {"_id": 0, "embedding": 0})
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found")
    return chunk
