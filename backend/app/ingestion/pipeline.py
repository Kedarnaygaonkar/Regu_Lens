"""
ReguLens Document Ingestion Pipeline.

Implements the full pipeline:
    PDF → extract → detect structure → chunk → detect duplicates →
    detect relationships → embed → store in MongoDB Atlas

The pipeline is idempotent — uploading the same PDF twice will not
create duplicate documents (enforced by content_hash).
"""
from __future__ import annotations

import logging
import os
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.database import Collections, get_sync_db
from app.ingestion.pdf_extractor import ExtractedDocument, extract_pdf
from app.ingestion.structure_detector import DetectedSection, detect_structure
from app.ingestion.chunker import structure_aware_chunk
from app.ingestion.naive_chunker import naive_chunk_text
from app.models.chunk import ChunkModel
from app.models.document import DocumentCreate, DocumentModel, DocumentStatus
from app.models.section import SectionModel
from app.utils.hashing import file_sha256, sha256_hash
from app.utils.logging import get_logger

logger = get_logger(__name__)


class IngestionResult:
    def __init__(self):
        self.document_id: Optional[str] = None
        self.was_duplicate: bool = False
        self.sections_created: int = 0
        self.chunks_created: int = 0
        self.naive_chunks_created: int = 0
        self.elapsed_seconds: float = 0.0
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "was_duplicate": self.was_duplicate,
            "sections_created": self.sections_created,
            "chunks_created": self.chunks_created,
            "naive_chunks_created": self.naive_chunks_created,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _save_upload(pdf_path: str, upload_dir: str) -> str:
    """Copy uploaded PDF to the upload directory and return stored path."""
    os.makedirs(upload_dir, exist_ok=True)
    filename = Path(pdf_path).name
    dest = os.path.join(upload_dir, filename)
    if pdf_path != dest:
        shutil.copy2(pdf_path, dest)
    return dest


def _store_document(
    db,
    doc_model: DocumentModel,
) -> str:
    """Upsert document record. Returns the document_id."""
    col = db[Collections.DOCUMENTS]
    doc_dict = doc_model.model_dump()
    # Use content_hash for idempotency
    existing = col.find_one({"content_hash": doc_model.content_hash})
    if existing:
        logger.info(f"Document already exists (content_hash match): {existing['document_id']}")
        return existing["document_id"], True

    col.insert_one(doc_dict)
    return doc_model.document_id, False


def _store_sections(
    db,
    document_id: str,
    sections: List[DetectedSection],
) -> Dict[str, str]:
    """
    Store detected sections. Returns a map of section_number → section_id.
    Skips sections whose content_hash already exists for this document.
    """
    col = db[Collections.SECTIONS]
    section_id_map: Dict[str, str] = {}

    for sec in sections:
        section_id = str(uuid.uuid4())
        content_hash = sha256_hash(sec.text)

        # Check existing
        existing = col.find_one({"document_id": document_id, "content_hash": content_hash})
        if existing:
            section_id_map[sec.section_number] = existing["section_id"]
            continue

        sec_model = SectionModel(
            section_id=section_id,
            document_id=document_id,
            section_number=sec.section_number,
            section_title=sec.section_title,
            parent_section_id=None,  # Will be resolved post-insert
            page_start=sec.page_start,
            page_end=sec.page_end,
            section_path=sec.section_path,
            text=sec.text,
            tables=sec.tables,
            footnotes=sec.footnotes,
            references=sec.references,
            content_hash=content_hash,
        )
        col.insert_one(sec_model.model_dump())
        section_id_map[sec.section_number] = section_id

    # Resolve parent_section_id
    for sec in sections:
        if sec.parent_section_number and sec.parent_section_number in section_id_map:
            parent_id = section_id_map[sec.parent_section_number]
            sec_id = section_id_map.get(sec.section_number)
            if sec_id:
                col.update_one(
                    {"section_id": sec_id},
                    {"$set": {"parent_section_id": parent_id}},
                )

    return section_id_map


def _store_chunks(db, chunks: List[ChunkModel]) -> int:
    """Store chunks, skipping exact duplicates by content_hash+document_id."""
    col = db[Collections.CHUNKS]
    stored = 0
    for chunk in chunks:
        existing = col.find_one(
            {"document_id": chunk.document_id, "content_hash": chunk.content_hash}
        )
        if existing:
            continue
        col.insert_one(chunk.model_dump())
        stored += 1
    return stored


def ingest_pdf(
    pdf_path: str,
    document_meta: DocumentCreate,
    use_structure_aware: bool = True,
    also_create_naive_chunks: bool = True,
    embedding_provider=None,  # Injected after embedding module is ready
) -> IngestionResult:
    """
    Main ingestion entry point.

    Args:
        pdf_path: Path to the PDF file.
        document_meta: User-supplied metadata (title, issuer, etc.).
        use_structure_aware: If True, create structure-aware chunks.
        also_create_naive_chunks: If True, also create naive chunks (for System A comparison).
        embedding_provider: Optional embedding provider (skipped if None).

    Returns:
        IngestionResult with statistics.
    """
    result = IngestionResult()
    start_time = time.time()
    settings = get_settings()
    db = get_sync_db()

    try:
        # ── Step 1: Compute file hash ────────────────────────────────────────
        logger.info(f"Starting ingestion: {pdf_path}")
        content_hash = file_sha256(pdf_path)

        # ── Step 2: Check for exact duplicate ────────────────────────────────
        existing = db[Collections.DOCUMENTS].find_one({"content_hash": content_hash})
        if existing:
            logger.info(f"Exact duplicate detected: {existing['document_id']}")
            result.document_id = existing["document_id"]
            result.was_duplicate = True
            result.elapsed_seconds = time.time() - start_time
            return result

        # ── Step 3: Save file ─────────────────────────────────────────────────
        stored_path = _save_upload(pdf_path, settings.upload_dir)

        # ── Step 4: Extract PDF ───────────────────────────────────────────────
        extracted: ExtractedDocument = extract_pdf(pdf_path)

        if extracted.is_empty:
            result.errors.append("PDF extraction yielded empty text")
            result.elapsed_seconds = time.time() - start_time
            return result

        # ── Step 5: Detect structure ──────────────────────────────────────────
        sections: List[DetectedSection] = detect_structure(extracted)

        # ── Step 6: Create document record ────────────────────────────────────
        document_id = str(uuid.uuid4())
        
        # Derive summary from first ~500 chars of text
        summary = (extracted.full_text[:500] + "…") if len(extracted.full_text) > 500 else extracted.full_text

        doc_model = DocumentModel(
            document_id=document_id,
            title=document_meta.title or extracted.metadata.get("title", extracted.filename),
            issuer=document_meta.issuer,
            document_type=document_meta.document_type,
            source_url=document_meta.source_url,
            original_filename=extracted.filename,
            publication_date=document_meta.publication_date,
            effective_date=document_meta.effective_date,
            version=document_meta.version,
            status=document_meta.status,
            summary=summary,
            file_path=stored_path,
            content_hash=content_hash,
            metadata={
                **document_meta.metadata,
                "pdf_metadata": extracted.metadata,
                "total_pages": extracted.total_pages,
                "extraction_method": extracted.extraction_method,
            },
        )

        doc_id, was_dup = _store_document(db, doc_model)
        if was_dup:
            result.document_id = doc_id
            result.was_duplicate = True
            result.elapsed_seconds = time.time() - start_time
            return result

        result.document_id = document_id

        # ── Step 7: Store sections ────────────────────────────────────────────
        section_id_map = _store_sections(db, document_id, sections)
        result.sections_created = len(section_id_map)

        # ── Step 8: Create structure-aware chunks ─────────────────────────────
        if use_structure_aware:
            struct_chunks = structure_aware_chunk(
                sections=sections,
                document_id=document_id,
                section_ids=section_id_map,
                max_chunk_chars=settings.structure_aware_max_chunk_size * 4,
                document_status=document_meta.status.value,
                effective_date=document_meta.effective_date,
            )
            # Mark these as structure-aware
            for c in struct_chunks:
                c.metadata["chunking_strategy"] = "structure_aware"
            stored = _store_chunks(db, struct_chunks)
            result.chunks_created = stored

        # ── Step 9: Create naive chunks (for System A) ────────────────────────
        if also_create_naive_chunks:
            naive_chunks = naive_chunk_text(
                text=extracted.full_text,
                document_id=document_id,
                chunk_size=settings.naive_chunk_size,
                overlap=settings.naive_chunk_overlap,
                document_status=document_meta.status.value,
            )
            for c in naive_chunks:
                c.metadata["chunking_strategy"] = "naive"
                # Mark different content_hash to avoid collision with structure chunks
                c.content_hash = sha256_hash(c.text + ":naive")
            stored_naive = _store_chunks(db, naive_chunks)
            result.naive_chunks_created = stored_naive

        # ── Step 10: Generate embeddings (if provider available) ──────────────
        if embedding_provider is not None:
            _embed_chunks(db, document_id, embedding_provider, strategy="structure_aware")

        result.elapsed_seconds = time.time() - start_time
        logger.info(
            f"Ingestion complete: doc_id={document_id}, "
            f"sections={result.sections_created}, "
            f"chunks={result.chunks_created}, "
            f"elapsed={result.elapsed_seconds:.2f}s"
        )
        return result

    except Exception as exc:
        logger.error(f"Ingestion failed: {exc}", exc_info=True)
        result.errors.append(str(exc))
        result.elapsed_seconds = time.time() - start_time
        return result


def _embed_chunks(db, document_id: str, embedding_provider, strategy: str = "structure_aware") -> None:
    """Generate and store embeddings for un-embedded chunks of a document."""
    col = db[Collections.CHUNKS]
    chunks_cursor = col.find(
        {
            "document_id": document_id,
            "embedding": None,
            "metadata.chunking_strategy": strategy,
        }
    )
    chunks = list(chunks_cursor)
    if not chunks:
        return

    texts = [c["text"] for c in chunks]
    logger.info(f"Embedding {len(texts)} chunks for document {document_id}")

    try:
        embeddings = embedding_provider.embed_texts(texts)
        for chunk_doc, embedding in zip(chunks, embeddings):
            col.update_one(
                {"chunk_id": chunk_doc["chunk_id"]},
                {
                    "$set": {
                        "embedding": embedding,
                        "embedding_model": embedding_provider.model_name,
                        "embedding_version": "1.0",
                    }
                },
            )
        logger.info(f"Stored {len(embeddings)} embeddings for document {document_id}")
    except Exception as e:
        logger.error(f"Embedding failed for document {document_id}: {e}")
        raise
