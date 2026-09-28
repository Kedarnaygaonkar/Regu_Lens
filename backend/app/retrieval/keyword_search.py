"""
MongoDB Atlas Search (full-text / keyword) retrieval for ReguLens.
Uses the $search aggregation stage with Atlas Search indexes.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.database import Collections, get_sync_db

logger = logging.getLogger(__name__)

# Atlas Search index name
TEXT_INDEX_NAME = "chunks_text_index"


def keyword_search(
    query: str,
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    include_superseded: bool = False,
) -> List[Dict[str, Any]]:
    """
    Perform MongoDB Atlas Search (full-text) on the chunks collection.

    Args:
        query: User query string.
        top_k: Number of results to return.
        filters: Optional metadata filters.
        include_superseded: If False, exclude SUPERSEDED/HISTORICAL chunks.

    Returns:
        List of chunk dicts with 'keyword_score' field.
    """
    db = get_sync_db()
    chunks_col = db[Collections.CHUNKS]

    must_clauses = [
        {
            "text": {
                "query": query,
                "path": "text",
                "fuzzy": {"maxEdits": 1},
            }
        }
    ]

    # Status filter
    if not include_superseded:
        must_clauses.append({
            "in": {
                "path": "document_status",
                "value": ["CURRENT", "AMENDED", "PARTIALLY_SUPERSEDED", "UNKNOWN"],
            }
        })

    search_stage = {
        "$search": {
            "index": TEXT_INDEX_NAME,
            "compound": {
                "must": must_clauses,
            },
        }
    }

    pipeline = [
        search_stage,
        {
            "$addFields": {
                "keyword_score": {"$meta": "searchScore"},
            }
        },
        {"$limit": top_k},
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
                "keyword_score": 1,
            }
        },
    ]

    try:
        results = list(chunks_col.aggregate(pipeline))
        logger.debug(f"Keyword search returned {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        return []


def document_text_search(
    query: str,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """Search in the documents collection by title/metadata."""
    db = get_sync_db()
    docs_col = db[Collections.DOCUMENTS]

    pipeline = [
        {
            "$search": {
                "index": "documents_text_index",
                "text": {
                    "query": query,
                    "path": ["title", "summary", "issuer"],
                    "fuzzy": {"maxEdits": 1},
                },
            }
        },
        {"$addFields": {"search_score": {"$meta": "searchScore"}}},
        {"$limit": top_k},
        {"$project": {"_id": 0, "document_id": 1, "title": 1, "issuer": 1, "status": 1, "search_score": 1}},
    ]

    try:
        return list(docs_col.aggregate(pipeline))
    except Exception as e:
        logger.error(f"Document text search failed: {e}")
        return []
