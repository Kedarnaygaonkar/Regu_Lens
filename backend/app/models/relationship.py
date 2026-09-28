"""Pydantic models for document relationships (supersession graph)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    AMENDS = "AMENDS"
    SUPERSEDES = "SUPERSEDES"
    PARTIALLY_AMENDS = "PARTIALLY_AMENDS"
    CONSOLIDATES = "CONSOLIDATES"
    REPLACES = "REPLACES"
    CLARIFIES = "CLARIFIES"
    REFERENCES = "REFERENCES"


class DocumentRelationship(BaseModel):
    relationship_id: str
    source_document_id: str  # newer doc
    target_document_id: str  # older doc
    relationship_type: RelationshipType
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)  # textual evidence
    affected_sections: Optional[List[str]] = None  # for PARTIALLY_AMENDS
    effective_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class DocumentRelationshipCreate(BaseModel):
    source_document_id: str
    target_document_id: str
    relationship_type: RelationshipType
    confidence: float = 1.0
    evidence: List[str] = Field(default_factory=list)
    affected_sections: Optional[List[str]] = None
    effective_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
