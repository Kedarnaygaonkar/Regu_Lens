"""
Naive chunker (Baseline / System A).
Fixed-size chunking with configurable overlap.
Used for comparison against the structure-aware chunker.
"""
from __future__ import annotations

import logging
import uuid
from typing import List

from app.models.chunk import ChunkModel, ChunkType
from app.utils.hashing import sha256_hash
from app.utils.text_utils import count_tokens_approx

logger = logging.getLogger(__name__)


def naive_chunk_text(
    text: str,
    document_id: str,
    chunk_size: int = 512,
    overlap: int = 64,
    page_start: int = 1,
    document_status: str = "UNKNOWN",
) -> List[ChunkModel]:
    """
    Split text into fixed-size overlapping chunks.
    chunk_size and overlap are measured in approximate tokens (chars/4).
    """
    chars_per_chunk = chunk_size * 4
    chars_overlap = overlap * 4

    chunks = []
    start = 0
    chunk_index = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chars_per_chunk, text_len)
        chunk_text = text[start:end].strip()

        if chunk_text:
            chunk_id = str(uuid.uuid4())
            chunks.append(
                ChunkModel(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    section_id=None,
                    chunk_index=chunk_index,
                    text=chunk_text,
                    page_start=page_start,
                    page_end=page_start,
                    content_hash=sha256_hash(chunk_text),
                    chunk_type=ChunkType.TEXT,
                    document_status=document_status,
                )
            )
            chunk_index += 1

        start += chars_per_chunk - chars_overlap

    logger.debug(
        f"Naive chunker: {len(chunks)} chunks from {len(text)} chars "
        f"(size={chunk_size}, overlap={overlap})"
    )
    return chunks
