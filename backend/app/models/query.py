"""Pydantic models for queries and RAG answers."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnswerStatus(str, Enum):
    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class Citation(BaseModel):
    document_id: str
    title: str
    issuer: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    effective_date: Optional[datetime] = None
    document_status: Optional[str] = None
    claim_supported: str
    text_excerpt: Optional[str] = None


class SupersessionNote(BaseModel):
    description: str
    source_document_id: Optional[str] = None
    target_document_id: Optional[str] = None
    relationship_type: Optional[str] = None
    effective_date: Optional[datetime] = None


class EvidenceNode(BaseModel):
    """A node in the evidence graph."""
    node_id: str
    node_type: str  # "document", "section", "chunk", "claim"
    label: str
    document_id: Optional[str] = None
    section_number: Optional[str] = None
    page: Optional[int] = None
    text: Optional[str] = None


class EvidenceGraph(BaseModel):
    nodes: List[EvidenceNode] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)


class QueryRequest(BaseModel):
    query: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=10, ge=1, le=50)
    use_hybrid: bool = True
    include_superseded: bool = False


class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total: int
    latency_ms: float


class AskRequest(BaseModel):
    question: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=10, ge=1, le=50)
    include_superseded: bool = False
    use_cross_document_reasoning: bool = True


class AskResponse(BaseModel):
    question: str
    answer: str
    status: AnswerStatus
    citations: List[Citation] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    related_documents: List[Dict[str, Any]] = Field(default_factory=list)
    supersession_notes: List[SupersessionNote] = Field(default_factory=list)
    evidence_graph: Optional[EvidenceGraph] = None
    latency_ms: float = 0.0
    retrieved_chunk_ids: List[str] = Field(default_factory=list)


class QueryLog(BaseModel):
    query: str
    retrieved_chunks: List[str] = Field(default_factory=list)
    retrieved_documents: List[str] = Field(default_factory=list)
    answer: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    latency: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
