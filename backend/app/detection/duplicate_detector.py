"""
Duplicate Detector for ReguLens.

Implements three levels of duplicate detection:
1. Exact duplicates — via SHA-256 content_hash
2. Near-duplicates — via RapidFuzz edit distance
3. Semantic similarity — via cosine similarity on embeddings

Important: Duplicates are NEVER deleted.
All provenance relationships are preserved in the duplicate_groups collection.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from rapidfuzz import fuzz

from app.database import Collections, get_sync_db
from app.utils.hashing import normalize_text

logger = logging.getLogger(__name__)

# Thresholds
EXACT_THRESHOLD = 1.0       # hash match
NEAR_DUP_THRESHOLD = 0.90   # RapidFuzz token_set_ratio / 100
SEMANTIC_THRESHOLD = 0.92   # cosine similarity


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


def _text_similarity(a: str, b: str) -> float:
    """Compute normalized token-set ratio similarity in [0, 1]."""
    return fuzz.token_set_ratio(normalize_text(a), normalize_text(b)) / 100.0


def detect_exact_duplicates(document_id: str) -> List[Dict[str, Any]]:
    """
    Find all chunks in other documents with the same content_hash.
    Creates/updates duplicate_groups records.
    Returns list of group records created.
    """
    db = get_sync_db()
    chunks_col = db[Collections.CHUNKS]
    groups_col = db[Collections.DUPLICATE_GROUPS]

    # Get all chunks for this document
    our_chunks = list(chunks_col.find({"document_id": document_id}, {"chunk_id": 1, "content_hash": 1, "text": 1}))
    groups_created = []

    for chunk in our_chunks:
        content_hash = chunk.get("content_hash")
        if not content_hash:
            continue

        # Find other chunks with same hash
        duplicates = list(
            chunks_col.find(
                {"content_hash": content_hash, "chunk_id": {"$ne": chunk["chunk_id"]}},
                {"chunk_id": 1, "document_id": 1},
            )
        )

        if not duplicates:
            continue

        # Check if group already exists
        existing_group = groups_col.find_one({"canonical_chunk_id": chunk["chunk_id"]})
        if existing_group:
            continue

        group_id = str(uuid.uuid4())
        group = {
            "group_id": group_id,
            "canonical_chunk_id": chunk["chunk_id"],
            "members": [{"chunk_id": d["chunk_id"], "document_id": d["document_id"]} for d in duplicates],
            "similarity_type": "EXACT",
            "similarity_score": 1.0,
            "created_at": __import__("datetime").datetime.utcnow(),
        }
        groups_col.insert_one(group)
        groups_created.append(group)
        logger.debug(f"Exact duplicate group created: {group_id} ({len(duplicates)} duplicates)")

    return groups_created


def detect_near_duplicates(
    document_id: str,
    threshold: float = NEAR_DUP_THRESHOLD,
    compare_against_all: bool = False,
) -> List[Dict[str, Any]]:
    """
    Find near-duplicate chunks using text similarity.
    Compares chunks in document_id against all other document chunks.
    
    For large corpora, this is O(N²) — should be run offline/batch.
    """
    db = get_sync_db()
    chunks_col = db[Collections.CHUNKS]
    groups_col = db[Collections.DUPLICATE_GROUPS]

    our_chunks = list(chunks_col.find(
        {"document_id": document_id, "metadata.chunking_strategy": "structure_aware"},
        {"chunk_id": 1, "text": 1, "document_id": 1},
    ))

    if compare_against_all:
        other_chunks = list(chunks_col.find(
            {"document_id": {"$ne": document_id}, "metadata.chunking_strategy": "structure_aware"},
            {"chunk_id": 1, "text": 1, "document_id": 1},
        ))
    else:
        other_chunks = []

    groups_created = []
    for our_c in our_chunks:
        near_dups = []
        for other_c in other_chunks:
            score = _text_similarity(our_c["text"], other_c["text"])
            if score >= threshold:
                near_dups.append({
                    "chunk_id": other_c["chunk_id"],
                    "document_id": other_c["document_id"],
                    "similarity_score": score,
                })

        if not near_dups:
            continue

        # Check if near-dup group already exists
        existing = groups_col.find_one({"canonical_chunk_id": our_c["chunk_id"], "similarity_type": "NEAR_DUPLICATE"})
        if existing:
            continue

        group_id = str(uuid.uuid4())
        best_score = max(d["similarity_score"] for d in near_dups)
        group = {
            "group_id": group_id,
            "canonical_chunk_id": our_c["chunk_id"],
            "members": near_dups,
            "similarity_type": "NEAR_DUPLICATE",
            "similarity_score": best_score,
            "created_at": __import__("datetime").datetime.utcnow(),
        }
        groups_col.insert_one(group)
        groups_created.append(group)

    logger.info(f"Near-duplicate detection: {len(groups_created)} groups for document {document_id}")
    return groups_created


def detect_semantic_duplicates(
    document_id: str,
    threshold: float = SEMANTIC_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    Find semantically similar chunks using cosine similarity on stored embeddings.
    Only runs if embeddings exist.
    """
    db = get_sync_db()
    chunks_col = db[Collections.CHUNKS]
    groups_col = db[Collections.DUPLICATE_GROUPS]

    our_chunks = list(chunks_col.find(
        {"document_id": document_id, "embedding": {"$ne": None}},
        {"chunk_id": 1, "text": 1, "embedding": 1, "document_id": 1},
    ))

    if not our_chunks:
        logger.info(f"No embedded chunks found for document {document_id}; skipping semantic dedup")
        return []

    # Get other embedded chunks (excluding same document)
    other_chunks = list(chunks_col.find(
        {"document_id": {"$ne": document_id}, "embedding": {"$ne": None}},
        {"chunk_id": 1, "embedding": 1, "document_id": 1},
    ))

    groups_created = []
    for our_c in our_chunks:
        if not our_c.get("embedding"):
            continue
        sem_dups = []
        for other_c in other_chunks:
            if not other_c.get("embedding"):
                continue
            score = _cosine_similarity(our_c["embedding"], other_c["embedding"])
            if score >= threshold:
                sem_dups.append({
                    "chunk_id": other_c["chunk_id"],
                    "document_id": other_c["document_id"],
                    "similarity_score": float(score),
                })

        if not sem_dups:
            continue

        existing = groups_col.find_one({"canonical_chunk_id": our_c["chunk_id"], "similarity_type": "SEMANTIC"})
        if existing:
            continue

        group_id = str(uuid.uuid4())
        best_score = max(d["similarity_score"] for d in sem_dups)
        group = {
            "group_id": group_id,
            "canonical_chunk_id": our_c["chunk_id"],
            "members": sem_dups,
            "similarity_type": "SEMANTIC",
            "similarity_score": best_score,
            "created_at": __import__("datetime").datetime.utcnow(),
        }
        groups_col.insert_one(group)
        groups_created.append(group)

    logger.info(f"Semantic duplicate detection: {len(groups_created)} groups for document {document_id}")
    return groups_created


def run_full_duplicate_detection(document_id: str) -> Dict[str, int]:
    """Run all three duplicate detection strategies for a document."""
    exact = detect_exact_duplicates(document_id)
    near = detect_near_duplicates(document_id, compare_against_all=True)
    semantic = detect_semantic_duplicates(document_id)
    return {
        "exact_groups": len(exact),
        "near_duplicate_groups": len(near),
        "semantic_groups": len(semantic),
    }
