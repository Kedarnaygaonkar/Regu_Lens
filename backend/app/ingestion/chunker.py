"""
Structure-Aware Chunker (System B — ReguLens).
Chunks based on:
  - section boundaries
  - subsection boundaries
  - paragraph boundaries
  - tables (never split)
  - footnotes
  - lists
  - annexures
  - cross-references

Every chunk preserves:
  - document_id
  - section_number
  - section_title
  - parent_section
  - section_path
  - page_start / page_end
  - content_hash
  - chunk_type
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from app.ingestion.structure_detector import DetectedSection
from app.models.chunk import ChunkModel, ChunkType
from app.utils.hashing import sha256_hash
from app.utils.text_utils import count_tokens_approx

logger = logging.getLogger(__name__)

# Table marker injected during structure detection
TABLE_PLACEHOLDER = "__TABLE_BLOCK__"


def _make_chunk(
    text: str,
    document_id: str,
    section: DetectedSection,
    section_id: str,
    chunk_index: int,
    chunk_type: ChunkType = ChunkType.TEXT,
    document_status: str = "UNKNOWN",
    effective_date: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ChunkModel:
    """Create a ChunkModel with full provenance."""
    return ChunkModel(
        chunk_id=str(uuid.uuid4()),
        document_id=document_id,
        section_id=section_id,
        chunk_index=chunk_index,
        text=text.strip(),
        page_start=section.page_start,
        page_end=section.page_end,
        section_number=section.section_number,
        section_title=section.section_title,
        parent_section=section.section_path,
        content_hash=sha256_hash(text.strip()),
        chunk_type=chunk_type,
        document_status=document_status,
        effective_date=effective_date,
        metadata=metadata or {
            "section_path": section.section_path,
            "section_level": section.level,
        },
    )


def _split_large_text(
    text: str,
    max_chars: int,
    split_pattern: re.Pattern,
) -> List[str]:
    """
    Split text at paragraph or sentence boundaries, never exceeding max_chars.
    Preserves paragraph/sentence integrity.
    """
    if len(text) <= max_chars:
        return [text]

    parts = split_pattern.split(text)
    chunks = []
    current = []
    current_len = 0

    for part in parts:
        part = part.strip()
        if not part:
            continue
        part_len = len(part)

        if current_len + part_len > max_chars and current:
            chunks.append("\n\n".join(current))
            current = [part]
            current_len = part_len
        else:
            current.append(part)
            current_len += part_len + 2  # +2 for "\n\n"

    if current:
        chunks.append("\n\n".join(current))

    return chunks if chunks else [text[:max_chars]]


# Paragraph boundary pattern
PARA_SPLIT = re.compile(r"\n\n+")
# Sentence boundary pattern (fallback)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def structure_aware_chunk(
    sections: List[DetectedSection],
    document_id: str,
    section_ids: Dict[str, str],  # section_number → section_id
    max_chunk_chars: int = 4096,
    document_status: str = "UNKNOWN",
    effective_date: Optional[Any] = None,
) -> List[ChunkModel]:
    """
    Generate structure-aware chunks from detected sections.
    
    Args:
        sections: List of DetectedSection objects
        document_id: Parent document ID
        section_ids: Map from section_number to MongoDB section_id
        max_chunk_chars: Maximum characters per chunk
        document_status: Status of parent document
        effective_date: Effective date of parent document
        
    Returns:
        List of ChunkModel objects with full provenance
    """
    chunks: List[ChunkModel] = []
    global_chunk_index = 0

    for section in sections:
        sec_id = section_ids.get(section.section_number, str(uuid.uuid4()))

        # 1. Tables — never split
        for table in section.tables:
            table_text = _table_to_text(table)
            if table_text:
                chunk = _make_chunk(
                    text=table_text,
                    document_id=document_id,
                    section=section,
                    section_id=sec_id,
                    chunk_index=global_chunk_index,
                    chunk_type=ChunkType.TABLE,
                    document_status=document_status,
                    effective_date=effective_date,
                    metadata={
                        "section_path": section.section_path,
                        "section_level": section.level,
                        "is_table": True,
                        "table_page": table.get("page", section.page_start),
                    },
                )
                chunks.append(chunk)
                global_chunk_index += 1

        # 2. Body text — split at paragraph boundaries
        body_text = section.text
        if body_text.strip():
            sub_texts = _split_large_text(body_text, max_chunk_chars, PARA_SPLIT)
            for sub in sub_texts:
                sub = sub.strip()
                if not sub:
                    continue
                # If still too large, split at sentences
                if len(sub) > max_chunk_chars:
                    sentence_parts = _split_large_text(sub, max_chunk_chars, SENT_SPLIT)
                else:
                    sentence_parts = [sub]

                for part in sentence_parts:
                    part = part.strip()
                    if not part:
                        continue
                    chunk = _make_chunk(
                        text=part,
                        document_id=document_id,
                        section=section,
                        section_id=sec_id,
                        chunk_index=global_chunk_index,
                        chunk_type=ChunkType.TEXT,
                        document_status=document_status,
                        effective_date=effective_date,
                    )
                    chunks.append(chunk)
                    global_chunk_index += 1

        # 3. Footnotes — chunk separately
        for fn in section.footnotes:
            fn = fn.strip()
            if fn:
                chunk = _make_chunk(
                    text=fn,
                    document_id=document_id,
                    section=section,
                    section_id=sec_id,
                    chunk_index=global_chunk_index,
                    chunk_type=ChunkType.FOOTNOTE,
                    document_status=document_status,
                    effective_date=effective_date,
                )
                chunks.append(chunk)
                global_chunk_index += 1

        # 4. References — chunk separately
        if section.references:
            refs_text = "References: " + "; ".join(section.references)
            chunk = _make_chunk(
                text=refs_text,
                document_id=document_id,
                section=section,
                section_id=sec_id,
                chunk_index=global_chunk_index,
                chunk_type=ChunkType.REFERENCE,
                document_status=document_status,
                effective_date=effective_date,
            )
            chunks.append(chunk)
            global_chunk_index += 1

    logger.info(
        f"Structure-aware chunker: {len(chunks)} chunks from {len(sections)} sections "
        f"(max_chars={max_chunk_chars})"
    )
    return chunks


def _table_to_text(table: Dict[str, Any]) -> str:
    """Convert a table dict to markdown text representation."""
    rows = table.get("rows", [])
    if not rows:
        return ""

    lines = []
    for i, row in enumerate(rows):
        cells = [str(cell or "").replace("\n", " ").strip() for cell in row]
        lines.append(" | ".join(cells))
        if i == 0:
            lines.append(" | ".join(["---"] * len(cells)))

    return "\n".join(lines)
