"""
Documents API routes.
POST /documents/upload
POST /documents/ingest
GET  /documents
GET  /documents/{id}
GET  /documents/{id}/sections
GET  /documents/{id}/relationships
"""
from __future__ import annotations

import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import Collections, get_sync_db
from app.detection.supersession_engine import get_document_lineage
from app.embeddings import get_embedding_provider
from app.ingestion.pipeline import ingest_pdf
from app.models.document import DocumentCreate, DocumentStatus, DocumentType
from app.models.relationship import DocumentRelationshipCreate, RelationshipType
from app.detection.supersession_engine import create_relationship

router = APIRouter(prefix="/documents", tags=["Documents"])


def _get_embedding_provider():
    settings = get_settings()
    try:
        return get_embedding_provider(
            provider=settings.embedding_provider,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )
    except Exception:
        return None


@router.post("/upload", summary="Upload and ingest a PDF document")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    issuer: str = Form(...),
    document_type: DocumentType = Form(DocumentType.OTHER),
    status: DocumentStatus = Form(DocumentStatus.UNKNOWN),
    source_url: Optional[str] = Form(None),
    publication_date: Optional[str] = Form(None),
    effective_date: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
):
    """Upload a PDF and run the full ingestion pipeline."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    settings = get_settings()
    tmp_path = None

    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # Parse dates
        from datetime import datetime
        pub_dt = None
        eff_dt = None
        if publication_date:
            try:
                pub_dt = datetime.fromisoformat(publication_date)
            except ValueError:
                pass
        if effective_date:
            try:
                eff_dt = datetime.fromisoformat(effective_date)
            except ValueError:
                pass

        doc_meta = DocumentCreate(
            title=title,
            issuer=issuer,
            document_type=document_type,
            source_url=source_url,
            original_filename=file.filename,
            publication_date=pub_dt,
            effective_date=eff_dt,
            version=version,
            status=status,
        )

        emb_provider = _get_embedding_provider()
        result = ingest_pdf(
            pdf_path=tmp_path,
            document_meta=doc_meta,
            embedding_provider=emb_provider,
        )

        if result.errors:
            raise HTTPException(status_code=500, detail=f"Ingestion errors: {result.errors}")

        return result.to_dict()

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("", summary="List all documents")
def list_documents(
    status: Optional[str] = Query(None),
    issuer: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List documents with optional filtering."""
    db = get_sync_db()
    filter_doc: Dict[str, Any] = {}
    if status:
        filter_doc["status"] = status.upper()
    if issuer:
        filter_doc["issuer"] = {"$regex": issuer, "$options": "i"}
    if document_type:
        filter_doc["document_type"] = document_type.upper()

    docs = list(
        db[Collections.DOCUMENTS]
        .find(filter_doc, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    total = db[Collections.DOCUMENTS].count_documents(filter_doc)
    return {"documents": docs, "total": total, "skip": skip, "limit": limit}


@router.get("/{document_id}", summary="Get document details")
def get_document(document_id: str):
    """Get a single document by ID."""
    db = get_sync_db()
    doc = db[Collections.DOCUMENTS].find_one({"document_id": document_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    # Attach counts
    doc["section_count"] = db[Collections.SECTIONS].count_documents({"document_id": document_id})
    doc["chunk_count"] = db[Collections.CHUNKS].count_documents({"document_id": document_id})
    return doc


@router.get("/{document_id}/sections", summary="Get sections of a document")
def get_document_sections(document_id: str):
    """Get all sections of a document."""
    db = get_sync_db()
    sections = list(
        db[Collections.SECTIONS]
        .find({"document_id": document_id}, {"_id": 0, "embedding": 0})
        .sort("section_number", 1)
    )
    return {"document_id": document_id, "sections": sections, "total": len(sections)}


@router.get("/{document_id}/relationships", summary="Get document relationships")
def get_document_relationships(document_id: str):
    """Get all relationships (supersession graph) for a document."""
    lineage = get_document_lineage(document_id)
    return lineage


@router.post("/{document_id}/relationships", summary="Add a document relationship")
def add_document_relationship(document_id: str, rel: DocumentRelationshipCreate):
    """Manually define a relationship between two documents."""
    try:
        created = create_relationship(
            source_document_id=rel.source_document_id,
            target_document_id=rel.target_document_id,
            relationship_type=rel.relationship_type,
            confidence=rel.confidence,
            evidence=rel.evidence,
            affected_sections=rel.affected_sections,
            effective_date=rel.effective_date,
        )
        return created.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
