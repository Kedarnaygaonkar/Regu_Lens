"""
MongoDB Atlas Vector Search retrieval for ReguLens.
Uses the $vectorSearch aggregation stage.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.database import Collections, get_sync_db
from app.config import get_settings

logger = logging.getLogger(__name__)

# The Atlas Vector Search index name (must be created in Atlas UI or via API)
VECTOR_INDEX_NAME = "chunks_vector_index"


def vector_search(
    query_embedding: List[float],
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    include_superseded: bool = False,
) -> List[Dict[str, Any]]:
    """
    Perform MongoDB Atlas Vector Search on the chunks collection.

    Args:
        query_embedding: Query vector.
        top_k: Number of results to return.
        filters: Optional metadata filters (issuer, document_type, etc.)
        include_superseded: If False, exclude SUPERSEDED/HISTORICAL chunks.

    Returns:
        List of chunk dicts with added 'vector_score' field.
    """
    db = get_sync_db()
    chunks_col = db[Collections.CHUNKS]

    # Build the filter document
    filter_doc = _build_filter(filters, include_superseded)

    # MongoDB Atlas $vectorSearch pipeline
    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX_NAME,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": min(top_k * 10, 1000),
                "limit": top_k,
                **({"filter": filter_doc} if filter_doc else {}),
            }
        },
        {
            "$addFields": {
                "vector_score": {"$meta": "vectorSearchScore"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "chunk_id": 1,
                "document_id": 1,
                "section_id": 1,
                "section_number": 1,
                "section_title": 1,
                "parent_section": 1,
                "text": 1,
                "page_start": 1,
                "page_end": 1,
                "document_status": 1,
                "effective_date": 1,
                "chunk_type": 1,
                "content_hash": 1,
                "metadata": 1,
                "vector_score": 1,
            }
        },
    ]

    try:
        results = list(chunks_col.aggregate(pipeline))
        logger.debug(f"Vector search returned {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        # Atlas Vector Search index may not be created yet
        return []


def _build_filter(
    filters: Optional[Dict[str, Any]],
    include_superseded: bool,
) -> Optional[Dict[str, Any]]:
    """Build MongoDB filter for vector search."""
    conditions = []

    # Exclude superseded/historical by default
    if not include_superseded:
        conditions.append({
            "document_status": {
                "$nin": ["SUPERSEDED", "HISTORICAL"]
            }
        })

    if filters:
        # issuer filter
        if "issuer" in filters:
            conditions.append({"metadata.issuer": filters["issuer"]})
        # document_type filter
        if "document_type" in filters:
            conditions.append({"metadata.document_type": filters["document_type"]})
        # date range filter
        if "from_date" in filters or "to_date" in filters:
            date_filter = {}
            if "from_date" in filters:
                date_filter["$gte"] = filters["from_date"]
            if "to_date" in filters:
                date_filter["$lte"] = filters["to_date"]
            conditions.append({"effective_date": date_filter})
        # section filter
        if "section_number" in filters:
            conditions.append({"section_number": {"$regex": f"^{filters['section_number']}"}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}
