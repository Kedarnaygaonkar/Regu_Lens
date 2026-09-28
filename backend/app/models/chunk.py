"""Pydantic models for text chunks with embeddings."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChunkType(str, Enum):
    TEXT = "TEXT"
    TABLE = "TABLE"
    FOOTNOTE = "FOOTNOTE"
    LIST = "LIST"
    HEADING = "HEADING"
    REFERENCE = "REFERENCE"
    ANNEXURE = "ANNEXURE"


class ChunkModel(BaseModel):
    chunk_id: str
    document_id: str
    section_id: Optional[str] = None
    chunk_index: int
    text: str
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    embedding_version: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    parent_section: Optional[str] = None
    content_hash: str
    chunk_type: ChunkType = ChunkType.TEXT
    document_status: str = "UNKNOWN"
    effective_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class ChunkResponse(BaseModel):
    """Chunk returned during retrieval — includes relevance score."""
    chunk_id: str
    document_id: str
    document_title: Optional[str] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    text: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    document_status: str
    effective_date: Optional[datetime] = None
    score: float = 0.0
    score_type: str = "vector"  # "vector", "keyword", "hybrid"
    metadata: Dict[str, Any] = Field(default_factory=dict)
