"""
PDF Extractor for ReguLens.
Uses PyMuPDF (fitz) as primary parser with pdfplumber as fallback.
Extracts: text, tables, metadata, page-level content.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    page_num: int  # 1-indexed
    text: str
    tables: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    width: float = 0.0
    height: float = 0.0
    is_scanned: bool = False  # True if text is very sparse (may need OCR)


@dataclass
class ExtractedDocument:
    filename: str
    total_pages: int
    metadata: Dict[str, Any]
    pages: List[PageContent]
    full_text: str
    extraction_method: str  # "pymupdf" | "pdfplumber" | "ocr"

    @property
    def is_empty(self) -> bool:
        return not self.full_text.strip()


def _clean_page_text(text: str) -> str:
    """Clean page text extracted from PDF."""
    # Remove PDF artifacts
    text = re.sub(r"\x00", "", text)
    # Fix broken hyphenation
    text = re.sub(r"-\n(\w)", r"\1", text)
    # Normalize whitespace while preserving paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_with_pymupdf(pdf_path: str) -> ExtractedDocument:
    """Primary extraction using PyMuPDF."""
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    filename = Path(pdf_path).name
    
    # Extract PDF metadata
    meta = doc.metadata or {}
    metadata = {
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
        "subject": meta.get("subject", ""),
        "creator": meta.get("creator", ""),
        "producer": meta.get("producer", ""),
        "creation_date": meta.get("creationDate", ""),
        "mod_date": meta.get("modDate", ""),
        "page_count": doc.page_count,
    }

    pages = []
    full_text_parts = []

    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        page_num = page_idx + 1

        # Extract text with layout preservation
        text = page.get_text("text")
        text = _clean_page_text(text)

        # Detect scanned pages (very low text density)
        words = page.get_text("words")
        is_scanned = len(words) < 10 and len(text) < 100

        # Extract tables using PyMuPDF's table finder
        tables = []
        try:
            tab_finder = page.find_tables()
            for tab in tab_finder.tables:
                extracted = tab.extract()
                if extracted:
                    tables.append({
                        "bbox": list(tab.bbox),
                        "rows": extracted,
                        "page": page_num,
                    })
        except Exception as e:
            logger.debug(f"Table extraction failed on page {page_num}: {e}")

        rect = page.rect
        pc = PageContent(
            page_num=page_num,
            text=text,
            tables=tables,
            width=rect.width,
            height=rect.height,
            is_scanned=is_scanned,
        )
        pages.append(pc)

        if text:
            full_text_parts.append(f"[PAGE {page_num}]\n{text}")

    doc.close()

    return ExtractedDocument(
        filename=filename,
        total_pages=len(pages),
        metadata=metadata,
        pages=pages,
        full_text="\n\n".join(full_text_parts),
        extraction_method="pymupdf",
    )


def _extract_with_pdfplumber(pdf_path: str) -> ExtractedDocument:
    """Fallback extraction using pdfplumber (better for tables)."""
    import pdfplumber

    filename = Path(pdf_path).name
    pages = []
    full_text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        metadata = pdf.metadata or {}
        
        for page_idx, page in enumerate(pdf.pages):
            page_num = page_idx + 1
            text = page.extract_text() or ""
            text = _clean_page_text(text)

            # Extract tables
            tables = []
            for tab in page.extract_tables():
                if tab:
                    tables.append({
                        "rows": tab,
                        "page": page_num,
                    })

            is_scanned = len(text) < 100
            pc = PageContent(
                page_num=page_num,
                text=text,
                tables=tables,
                is_scanned=is_scanned,
            )
            pages.append(pc)
            if text:
                full_text_parts.append(f"[PAGE {page_num}]\n{text}")

    return ExtractedDocument(
        filename=filename,
        total_pages=len(pages),
        metadata=dict(metadata),
        pages=pages,
        full_text="\n\n".join(full_text_parts),
        extraction_method="pdfplumber",
    )


def extract_pdf(pdf_path: str) -> ExtractedDocument:
    """
    Extract content from a PDF file.
    Tries PyMuPDF first; falls back to pdfplumber if extraction fails or yields empty text.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info(f"Extracting PDF: {path.name}")

    # Try PyMuPDF first
    try:
        result = _extract_with_pymupdf(pdf_path)
        if not result.is_empty:
            logger.info(
                f"PyMuPDF extraction: {result.total_pages} pages, "
                f"{len(result.full_text)} chars"
            )
            return result
        logger.warning(f"PyMuPDF returned empty text, falling back to pdfplumber")
    except Exception as e:
        logger.warning(f"PyMuPDF failed: {e}, falling back to pdfplumber")

    # Fallback to pdfplumber
    try:
        result = _extract_with_pdfplumber(pdf_path)
        logger.info(
            f"pdfplumber extraction: {result.total_pages} pages, "
            f"{len(result.full_text)} chars"
        )
        return result
    except Exception as e:
        logger.error(f"pdfplumber also failed: {e}")
        raise RuntimeError(f"Failed to extract PDF {pdf_path}: {e}") from e
