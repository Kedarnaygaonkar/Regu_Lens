"""
Evidence Graph Builder for ReguLens.
Builds a traceable evidence graph:
  QUESTION → SUBQUERY → DOCUMENT → SECTION → CHUNK → CLAIM → ANSWER
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.models.query import EvidenceGraph, EvidenceNode


def build_evidence_graph(
    question: str,
    retrieved_chunks: List[Dict[str, Any]],
    citations: List[Dict[str, Any]],
    subqueries: Optional[List[str]] = None,
) -> EvidenceGraph:
    """Build a traceable evidence graph from retrieved chunks."""
    nodes: List[EvidenceNode] = []
    edges: List[Dict[str, Any]] = []

    # Root: question node
    q_node_id = "question_root"
    nodes.append(EvidenceNode(
        node_id=q_node_id,
        node_type="question",
        label=question[:100] + ("…" if len(question) > 100 else ""),
    ))

    # Subquery nodes
    sq_node_ids = []
    for i, sq in enumerate(subqueries or [question]):
        sq_id = f"subquery_{i}"
        nodes.append(EvidenceNode(
            node_id=sq_id,
            node_type="subquery",
            label=sq[:80] + ("…" if len(sq) > 80 else ""),
        ))
        edges.append({"from": q_node_id, "to": sq_id, "label": "decomposed_to"})
        sq_node_ids.append(sq_id)

    # Document → Section → Chunk nodes
    seen_docs: Dict[str, str] = {}  # document_id → node_id
    seen_sections: Dict[str, str] = {}  # section_id → node_id

    for i, chunk in enumerate(retrieved_chunks[:20]):  # Limit graph size
        doc_id = chunk.get("document_id", "")
        section_id = chunk.get("section_id", "")
        chunk_id = chunk.get("chunk_id", f"chunk_{i}")

        # Document node
        if doc_id not in seen_docs:
            doc_node_id = f"doc_{doc_id[:8]}"
            seen_docs[doc_id] = doc_node_id
            nodes.append(EvidenceNode(
                node_id=doc_node_id,
                node_type="document",
                label=chunk.get("document_title", doc_id[:30]),
                document_id=doc_id,
            ))
            # Link subquery → document
            for sq_id in sq_node_ids:
                edges.append({"from": sq_id, "to": doc_node_id, "label": "retrieved_from"})

        # Section node
        if section_id and section_id not in seen_sections:
            sec_node_id = f"sec_{section_id[:8]}"
            seen_sections[section_id] = sec_node_id
            nodes.append(EvidenceNode(
                node_id=sec_node_id,
                node_type="section",
                label=f"§{chunk.get('section_number', '')} {chunk.get('section_title', '')}",
                document_id=doc_id,
                section_number=chunk.get("section_number"),
            ))
            edges.append({"from": seen_docs[doc_id], "to": sec_node_id, "label": "contains"})

        # Chunk node
        chunk_node_id = f"chunk_{chunk_id[:8]}"
        text_preview = chunk.get("text", "")[:80] + "…"
        nodes.append(EvidenceNode(
            node_id=chunk_node_id,
            node_type="chunk",
            label=text_preview,
            document_id=doc_id,
            section_number=chunk.get("section_number"),
            page=chunk.get("page_start"),
            text=chunk.get("text", "")[:200],
        ))

        if section_id and section_id in seen_sections:
            edges.append({"from": seen_sections[section_id], "to": chunk_node_id, "label": "contains"})
        elif doc_id in seen_docs:
            edges.append({"from": seen_docs[doc_id], "to": chunk_node_id, "label": "contains"})

    # Answer node
    answer_node_id = "answer_root"
    nodes.append(EvidenceNode(
        node_id=answer_node_id,
        node_type="answer",
        label="Generated Answer",
    ))
    # Link chunks to answer via claims
    for citation in citations[:5]:
        chunk_claim_id = f"claim_{uuid.uuid4().hex[:6]}"
        nodes.append(EvidenceNode(
            node_id=chunk_claim_id,
            node_type="claim",
            label=citation.get("claim_supported", "")[:80],
        ))
        doc_id = citation.get("document_id", "")
        if doc_id in seen_docs:
            edges.append({"from": seen_docs[doc_id], "to": chunk_claim_id, "label": "supports"})
        edges.append({"from": chunk_claim_id, "to": answer_node_id, "label": "contributes_to"})

    return EvidenceGraph(nodes=nodes, edges=edges)
