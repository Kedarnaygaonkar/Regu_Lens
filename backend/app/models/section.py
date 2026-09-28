"""Pydantic models for document sections."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SectionModel(BaseModel):
    section_id: str
    document_id: str
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    parent_section_id: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_path: Optional[str] = None  # e.g., "1 > 1.2 > 1.2.3"
    text: str = ""
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    footnotes: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    content_hash: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
