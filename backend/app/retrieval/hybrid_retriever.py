"""
Hybrid Retriever for ReguLens.

Pipeline:
  1. Vector search (MongoDB Atlas Vector Search)
  2. Keyword search (MongoDB Atlas Search)
  3. Candidate fusion (Reciprocal Rank Fusion)
  4. Duplicate reduction (collapse exact-hash matches)
  5. Version/supersession filtering
  6. Enrich with document metadata
  7. Return final evidence set

Each result contains: document, section, chunk, score, page,
publication date, effective date, status, relationship info.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.database import Collections, get_sync_db
from app.retrieval.vector_search import vector_search
from app.retrieval.keyword_search import keyword_search

logger = logging.getLogger(__name__)


def _reciprocal_rank_fusion(
    vector_results: List[Dict],
    keyword_results: List[Dict],
    k: int = 60,
) -> List[Dict]:
    """
    Combine vector and keyword results using Reciprocal Rank Fusion (RRF).
    RRF score = 1/(k + rank)
    """
    scores: Dict[str, float] = {}
    chunk_map: Dict[str, Dict] = {}

    # Vector results
    for rank, result in enumerate(vector_results, start=1):
        chunk_id = result["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
        if chunk_id not in chunk_map:
            chunk_map[chunk_id] = {**result, "score_type": "hybrid"}

    # Keyword results
    for rank, result in enumerate(keyword_results, start=1):
        chunk_id = result["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
        if chunk_id not in chunk_map:
            chunk_map[chunk_id] = {**result, "score_type": "hybrid"}

    # Sort by RRF score descending
    sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    results = []
    for cid in sorted_ids:
        chunk = chunk_map[cid]
        chunk["hybrid_score"] = scores[cid]
        results.append(chunk)

    return results


def _deduplicate_results(results: List[Dict]) -> List[Dict]:
    """
    Remove chunks with identical content_hash, keeping the one with highest score.
    Preserves provenance: documents that have the same clause still appear once
    but with cross-references in metadata.
    """
    seen_hashes: Dict[str, Dict] = {}

    for result in results:
        h = result.get("content_hash", result["chunk_id"])
        if h not in seen_hashes:
            seen_hashes[h] = result
            seen_hashes[h]["provenance_doc_ids"] = [result.get("document_id", "")]
        else:
            # Merge provenance
            existing = seen_hashes[h]
            doc_id = result.get("document_id", "")
            if doc_id and doc_id not in existing.get("provenance_doc_ids", []):
                existing.setdefault("provenance_doc_ids", []).append(doc_id)

    return list(seen_hashes.values())


def _enrich_with_document_info(results: List[Dict]) -> List[Dict]:
    """Add document metadata (title, issuer, dates, status) to each result."""
    db = get_sync_db()
    docs_col = db[Collections.DOCUMENTS]

    # Batch fetch documents
    doc_ids = list(set(r.get("document_id") for r in results if r.get("document_id")))
    docs = {
        d["document_id"]: d
        for d in docs_col.find(
            {"document_id": {"$in": doc_ids}},
            {"_id": 0, "document_id": 1, "title": 1, "issuer": 1, "status": 1,
             "publication_date": 1, "effective_date": 1, "document_type": 1,
             "version": 1, "source_url": 1},
        )
    }

    for result in results:
        doc_id = result.get("document_id")
        if doc_id and doc_id in docs:
            doc = docs[doc_id]
            result["document_title"] = doc.get("title", "")
            result["document_issuer"] = doc.get("issuer", "")
            result["publication_date"] = doc.get("publication_date")
            result["document_effective_date"] = doc.get("effective_date")
            result["document_version"] = doc.get("version")
            result["document_type"] = doc.get("document_type", "")
            result["source_url"] = doc.get("source_url")
            # Override document_status from document record (most authoritative)
            result["document_status"] = doc.get("status", result.get("document_status", "UNKNOWN"))

    return results


def hybrid_retrieve(
    query: str,
    query_embedding: List[float],
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    include_superseded: bool = False,
    use_vector: bool = True,
    use_keyword: bool = True,
) -> List[Dict[str, Any]]:
    """
    Main hybrid retrieval function.

    Returns ranked list of chunks with full provenance metadata.
    """
    vector_results = []
    keyword_results = []

    if use_vector and query_embedding:
        vector_results = vector_search(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # Over-fetch for fusion
            filters=filters,
            include_superseded=include_superseded,
        )

    if use_keyword:
        keyword_results = keyword_search(
            query=query,
            top_k=top_k * 2,
            filters=filters,
            include_superseded=include_superseded,
        )

    # Fallback: if Atlas Search isn't set up, use simple MongoDB text search
    if not vector_results and not keyword_results:
        keyword_results = _fallback_text_search(query, top_k * 2, include_superseded)

    # Fusion
    if vector_results or keyword_results:
        fused = _reciprocal_rank_fusion(vector_results, keyword_results)
    else:
        fused = []

    # Deduplicate
    deduped = _deduplicate_results(fused)

    # Enrich
    enriched = _enrich_with_document_info(deduped)

    # Take top-k
    final = enriched[:top_k]

    logger.info(
        f"Hybrid retrieval: {len(vector_results)} vector + {len(keyword_results)} keyword → "
        f"{len(final)} final results"
    )

    return final


def _fallback_text_search(
    query: str,
    top_k: int,
    include_superseded: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fallback full-text search using MongoDB $text operator.
    Used when Atlas Search index is not yet configured.
    """
    db = get_sync_db()
    chunks_col = db[Collections.CHUNKS]

    filter_doc: Dict[str, Any] = {}
    if not include_superseded:
        filter_doc["document_status"] = {"$nin": ["SUPERSEDED", "HISTORICAL"]}

    # Simple regex search on text
    words = query.split()[:5]  # Use first 5 words
    regex_parts = "|".join(words)
    filter_doc["text"] = {"$regex": regex_parts, "$options": "i"}

    projection = {
        "_id": 0,
        "chunk_id": 1, "document_id": 1, "section_id": 1,
        "section_number": 1, "section_title": 1, "parent_section": 1,
        "text": 1, "page_start": 1, "page_end": 1,
        "document_status": 1, "effective_date": 1,
        "chunk_type": 1, "content_hash": 1, "metadata": 1,
    }

    results = list(chunks_col.find(filter_doc, projection).limit(top_k))
    for r in results:
        r["keyword_score"] = 1.0
    return results
