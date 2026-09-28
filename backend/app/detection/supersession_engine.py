"""
Version and Supersession Engine for ReguLens.

Core feature: Tracks how documents relate to each other over time.
  2019 Circular → 2022 Amendment → 2024 Master Direction

Rules:
  - Never assume newest document is automatically current.
  - Use explicit textual evidence + manual definitions.
  - Store confidence score and evidence for every relationship.
  - Update document statuses based on detected relationships.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.database import Collections, get_sync_db
from app.models.relationship import DocumentRelationship, RelationshipType
from app.models.document import DocumentStatus
from app.utils.text_utils import detect_supersession_language, detect_circular_references

logger = logging.getLogger(__name__)

# Patterns that imply specific relationship types
RELATIONSHIP_PATTERNS = {
    RelationshipType.SUPERSEDES: [
        re.compile(r"supersed(?:es|ed|ing)\s+(?:the\s+)?(?:provisions?\s+of\s+)?", re.IGNORECASE),
        re.compile(r"in\s+supersession\s+of", re.IGNORECASE),
        re.compile(r"stand(?:s)?\s+(?:cancelled|rescinded|withdrawn)", re.IGNORECASE),
    ],
    RelationshipType.AMENDS: [
        re.compile(r"amend(?:s|ed|ment)\s+to", re.IGNORECASE),
        re.compile(r"modif(?:ies|ied|ication)\s+(?:the\s+)?", re.IGNORECASE),
        re.compile(r"substitut(?:es|ed|ing)\s+(?:the\s+)?", re.IGNORECASE),
    ],
    RelationshipType.PARTIALLY_AMENDS: [
        re.compile(r"in\s+partial\s+modification\s+of", re.IGNORECASE),
        re.compile(r"partial(?:ly)?\s+amend", re.IGNORECASE),
        re.compile(r"partial(?:ly)?\s+supersed", re.IGNORECASE),
    ],
    RelationshipType.CONSOLIDATES: [
        re.compile(r"consolidat(?:es|ed|ing)\s+(?:the\s+)?", re.IGNORECASE),
        re.compile(r"master\s+direction", re.IGNORECASE),
    ],
    RelationshipType.CLARIFIES: [
        re.compile(r"clarif(?:ies|ication)\s+(?:the\s+)?", re.IGNORECASE),
        re.compile(r"FAQ|frequently\s+asked", re.IGNORECASE),
    ],
    RelationshipType.REPLACES: [
        re.compile(r"replac(?:es|ed|ing)\s+(?:the\s+)?", re.IGNORECASE),
    ],
}


def detect_relationships_from_text(
    source_document_id: str,
    source_text: str,
    source_title: str = "",
) -> List[DocumentRelationship]:
    """
    Analyze text of a document to detect references to other documents
    and infer relationship types.

    Returns a list of detected DocumentRelationship objects (without target_document_id
    resolved — requires a second pass to match against known documents).
    """
    relationships = []
    
    # Extract supersession language
    supersession_snippets = detect_supersession_language(source_text)
    circular_refs = detect_circular_references(source_text)

    for snippet in supersession_snippets:
        rel_type = _classify_snippet(snippet)
        if rel_type is None:
            continue

        relationships.append({
            "source_document_id": source_document_id,
            "relationship_type": rel_type,
            "evidence": [snippet],
            "circular_refs": circular_refs,
            "confidence": _estimate_confidence(snippet, rel_type),
        })

    return relationships


def _classify_snippet(snippet: str) -> Optional[RelationshipType]:
    """Classify a supersession snippet into a RelationshipType."""
    for rel_type, patterns in RELATIONSHIP_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(snippet):
                return rel_type
    return RelationshipType.AMENDS  # Default if supersession language detected


def _estimate_confidence(snippet: str, rel_type: RelationshipType) -> float:
    """Estimate confidence score based on clarity of the evidence."""
    # Higher confidence for explicit phrases
    high_confidence = ["in supersession of", "supersedes", "stand cancelled", "replaces"]
    for phrase in high_confidence:
        if phrase.lower() in snippet.lower():
            return 0.95
    return 0.75


def create_relationship(
    source_document_id: str,
    target_document_id: str,
    relationship_type: RelationshipType,
    confidence: float = 1.0,
    evidence: Optional[List[str]] = None,
    affected_sections: Optional[List[str]] = None,
    effective_date: Optional[datetime] = None,
) -> DocumentRelationship:
    """
    Create and persist a document relationship.
    Also updates document statuses accordingly.
    """
    db = get_sync_db()
    rels_col = db[Collections.DOCUMENT_RELATIONSHIPS]
    docs_col = db[Collections.DOCUMENTS]

    # Check for existing relationship
    existing = rels_col.find_one({
        "source_document_id": source_document_id,
        "target_document_id": target_document_id,
        "relationship_type": relationship_type.value,
    })
    if existing:
        logger.info(f"Relationship already exists: {source_document_id} → {target_document_id} ({relationship_type.value})")
        return DocumentRelationship(**{k: v for k, v in existing.items() if k != "_id"})

    relationship_id = str(uuid.uuid4())
    rel = DocumentRelationship(
        relationship_id=relationship_id,
        source_document_id=source_document_id,
        target_document_id=target_document_id,
        relationship_type=relationship_type,
        confidence=confidence,
        evidence=evidence or [],
        affected_sections=affected_sections,
        effective_date=effective_date,
    )

    rels_col.insert_one(rel.model_dump())
    logger.info(
        f"Relationship created: {source_document_id} --[{relationship_type.value}]--> {target_document_id} "
        f"(confidence={confidence})"
    )

    # Update statuses
    _update_document_statuses(source_document_id, target_document_id, relationship_type, docs_col)

    return rel


def _update_document_statuses(
    source_id: str,
    target_id: str,
    rel_type: RelationshipType,
    docs_col,
) -> None:
    """
    Update document status fields based on relationship.

    Rules:
      SUPERSEDES → target becomes SUPERSEDED
      PARTIALLY_AMENDS → target becomes PARTIALLY_SUPERSEDED  
      AMENDS → target becomes AMENDED
      CONSOLIDATES → target becomes SUPERSEDED (consolidated into newer)
      REPLACES → target becomes SUPERSEDED
    """
    target_status = {
        RelationshipType.SUPERSEDES: DocumentStatus.SUPERSEDED,
        RelationshipType.PARTIALLY_AMENDS: DocumentStatus.PARTIALLY_SUPERSEDED,
        RelationshipType.AMENDS: DocumentStatus.AMENDED,
        RelationshipType.CONSOLIDATES: DocumentStatus.SUPERSEDED,
        RelationshipType.REPLACES: DocumentStatus.SUPERSEDED,
        RelationshipType.CLARIFIES: None,  # No status change
        RelationshipType.REFERENCES: None,
    }.get(rel_type)

    if target_status is not None:
        docs_col.update_one(
            {"document_id": target_id},
            {"$set": {"status": target_status.value, "updated_at": datetime.utcnow()}},
        )
        logger.info(f"Document {target_id} status updated to {target_status.value}")

    # Also update chunk statuses for the target document
    _update_chunk_statuses(target_id, target_status)


def _update_chunk_statuses(document_id: str, status: Optional[DocumentStatus]) -> None:
    """Cascade status change to all chunks of a document."""
    if status is None:
        return
    db = get_sync_db()
    db[Collections.CHUNKS].update_many(
        {"document_id": document_id},
        {"$set": {"document_status": status.value}},
    )


def get_document_lineage(document_id: str) -> Dict[str, Any]:
    """
    Get the full lineage of a document — all ancestors and descendants.
    Returns a graph structure.
    """
    db = get_sync_db()
    rels_col = db[Collections.DOCUMENT_RELATIONSHIPS]
    docs_col = db[Collections.DOCUMENTS]

    # Ancestors (documents that this document supersedes/amends)
    outgoing = list(rels_col.find({"source_document_id": document_id}))
    # Descendants (documents that supersede/amend this document)
    incoming = list(rels_col.find({"target_document_id": document_id}))

    def get_doc_info(doc_id: str) -> Dict[str, Any]:
        doc = docs_col.find_one({"document_id": doc_id}, {"_id": 0})
        if doc:
            return {
                "document_id": doc_id,
                "title": doc.get("title", ""),
                "status": doc.get("status", "UNKNOWN"),
                "publication_date": doc.get("publication_date"),
                "issuer": doc.get("issuer", ""),
            }
        return {"document_id": doc_id}

    lineage = {
        "document_id": document_id,
        "document_info": get_doc_info(document_id),
        "supersedes": [
            {
                **{k: v for k, v in r.items() if k != "_id"},
                "target_info": get_doc_info(r["target_document_id"]),
            }
            for r in outgoing
        ],
        "superseded_by": [
            {
                **{k: v for k, v in r.items() if k != "_id"},
                "source_info": get_doc_info(r["source_document_id"]),
            }
            for r in incoming
        ],
    }

    return lineage


def resolve_current_status(document_id: str) -> str:
    """
    Resolve the authoritative current status of a document by traversing the graph.
    Returns a DocumentStatus value string.
    """
    db = get_sync_db()
    doc = db[Collections.DOCUMENTS].find_one({"document_id": document_id}, {"status": 1})
    if not doc:
        return DocumentStatus.UNKNOWN.value

    # Check if any newer document supersedes/consolidates this one
    superseding = db[Collections.DOCUMENT_RELATIONSHIPS].find_one({
        "target_document_id": document_id,
        "relationship_type": {"$in": [
            RelationshipType.SUPERSEDES.value,
            RelationshipType.CONSOLIDATES.value,
            RelationshipType.REPLACES.value,
        ]},
    })

    if superseding:
        return DocumentStatus.SUPERSEDED.value

    partially = db[Collections.DOCUMENT_RELATIONSHIPS].find_one({
        "target_document_id": document_id,
        "relationship_type": RelationshipType.PARTIALLY_AMENDS.value,
    })
    if partially:
        return DocumentStatus.PARTIALLY_SUPERSEDED.value

    amended = db[Collections.DOCUMENT_RELATIONSHIPS].find_one({
        "target_document_id": document_id,
        "relationship_type": RelationshipType.AMENDS.value,
    })
    if amended:
        return DocumentStatus.AMENDED.value

    return doc.get("status", DocumentStatus.UNKNOWN.value)
