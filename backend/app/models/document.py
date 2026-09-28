"""Pydantic models for ReguLens documents."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    PARTIALLY_SUPERSEDED = "PARTIALLY_SUPERSEDED"
    AMENDED = "AMENDED"
    HISTORICAL = "HISTORICAL"
    UNKNOWN = "UNKNOWN"


class DocumentType(str, Enum):
    CIRCULAR = "CIRCULAR"
    MASTER_DIRECTION = "MASTER_DIRECTION"
    NOTIFICATION = "NOTIFICATION"
    ANNUAL_REPORT = "ANNUAL_REPORT"
    POLICY_DOCUMENT = "POLICY_DOCUMENT"
    AMENDMENT = "AMENDMENT"
    TERMS = "TERMS"
    OTHER = "OTHER"


class DocumentCreate(BaseModel):
    title: str
    issuer: str
    document_type: DocumentType = DocumentType.OTHER
    source_url: Optional[str] = None
    original_filename: str
    publication_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    version: Optional[str] = None
    status: DocumentStatus = DocumentStatus.UNKNOWN
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentModel(DocumentCreate):
    document_id: str
    summary: Optional[str] = None
    file_path: Optional[str] = None
    content_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class DocumentResponse(DocumentModel):
    id: Optional[str] = Field(default=None, alias="_id")
    section_count: int = 0
    chunk_count: int = 0

    class Config:
        populate_by_name = True
