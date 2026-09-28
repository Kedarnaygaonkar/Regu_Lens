"""Ingestion package."""
from app.ingestion.pdf_extractor import extract_pdf, ExtractedDocument, PageContent
from app.ingestion.structure_detector import detect_structure, DetectedSection
from app.ingestion.chunker import structure_aware_chunk
from app.ingestion.naive_chunker import naive_chunk_text
from app.ingestion.pipeline import ingest_pdf, IngestionResult

__all__ = [
    "extract_pdf", "ExtractedDocument", "PageContent",
    "detect_structure", "DetectedSection",
    "structure_aware_chunk",
    "naive_chunk_text",
    "ingest_pdf", "IngestionResult",
]
