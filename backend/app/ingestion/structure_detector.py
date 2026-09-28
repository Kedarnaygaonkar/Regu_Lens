"""
Structure Detector for ReguLens.
Detects sections, subsections, headings, footnotes, and references
from extracted page content.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.ingestion.pdf_extractor import ExtractedDocument, PageContent
from app.utils.text_utils import detect_headings, detect_circular_references

logger = logging.getLogger(__name__)


@dataclass
class DetectedSection:
    section_number: str
    section_title: str
    section_path: str  # e.g., "1 > 1.2 > 1.2.3"
    parent_section_number: Optional[str]
    page_start: int
    page_end: int
    text: str
    tables: List[Dict[str, Any]] = field(default_factory=list)
    footnotes: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    level: int = 1  # heading depth level


def _determine_level(section_number: str) -> int:
    """Return depth of a section number (e.g., '1.2.3' → 3)."""
    if not section_number or not re.match(r"[\d.]+", section_number):
        return 1
    return len(section_number.split("."))


def _get_parent_number(section_number: str) -> Optional[str]:
    """Return parent section number, e.g., '1.2.3' → '1.2'."""
    parts = section_number.split(".")
    if len(parts) <= 1:
        return None
    return ".".join(parts[:-1])


def _build_section_path(section_number: str, path_map: Dict[str, str]) -> str:
    """Build full path like '1 > 1.2 > 1.2.3'."""
    parts = section_number.split(".")
    path_parts = []
    for i in range(len(parts)):
        ancestor = ".".join(parts[: i + 1])
        path_parts.append(ancestor)
    return " > ".join(path_parts)


def _extract_footnotes(text: str) -> Tuple[str, List[str]]:
    """Extract footnotes from text, returning (clean_text, footnotes)."""
    footnote_pattern = re.compile(
        r"(?m)^\s*(?:\d+|[*†‡§])\s+(?:[A-Z].*?)(?=\n\s*(?:\d+|[*†‡§])\s+[A-Z]|\Z)",
        re.DOTALL,
    )
    # Simpler: detect footnote markers and trailing footnotes
    footnotes = []
    # Find footnote-like lines at the bottom of pages
    lines = text.split("\n")
    footnote_lines = []
    body_lines = []
    in_footnotes = False

    for line in lines:
        stripped = line.strip()
        if re.match(r"^(\d+|[*†‡§])\s+[A-Za-z]", stripped) and len(stripped) < 500:
            in_footnotes = True
        if in_footnotes and stripped:
            footnote_lines.append(stripped)
        else:
            body_lines.append(line)

    if footnote_lines:
        footnotes = footnote_lines

    return "\n".join(body_lines), footnotes


def detect_structure(doc: ExtractedDocument) -> List[DetectedSection]:
    """
    Detect document structure from extracted text.
    Returns a list of DetectedSection objects.
    """
    logger.info(f"Detecting structure in: {doc.filename}")

    # Build a combined page-aware text with page markers
    # We track which page each character belongs to
    page_char_map: List[int] = []  # page_num at each char position in full_text
    page_texts: Dict[int, str] = {}

    for page in doc.pages:
        page_texts[page.page_num] = page.text

    # Collect all headings from full document text
    full_text = doc.full_text
    headings = detect_headings(full_text)

    if not headings:
        logger.info("No structured headings detected; creating a single section")
        # Fallback: single section for the whole document
        refs = detect_circular_references(full_text)
        body, footnotes = _extract_footnotes(full_text)
        return [
            DetectedSection(
                section_number="1",
                section_title=doc.metadata.get("title", doc.filename),
                section_path="1",
                parent_section_number=None,
                page_start=1,
                page_end=doc.total_pages,
                text=body,
                footnotes=footnotes,
                references=refs,
                level=1,
            )
        ]

    # Build sections from headings
    sections = []
    path_map: Dict[str, str] = {}

    for idx, (sec_num, sec_title, char_offset) in enumerate(headings):
        # Determine page for this heading
        # Find nearest [PAGE N] marker before char_offset
        page_match = None
        for m in re.finditer(r"\[PAGE (\d+)\]", full_text[:char_offset]):
            page_match = m
        page_start = int(page_match.group(1)) if page_match else 1

        # Get text until next heading
        if idx + 1 < len(headings):
            next_offset = headings[idx + 1][2]
            section_text = full_text[char_offset:next_offset]
        else:
            section_text = full_text[char_offset:]

        # Determine page end
        page_end_match = None
        for m in re.finditer(r"\[PAGE (\d+)\]", section_text):
            page_end_match = m
        if page_end_match:
            page_end = int(page_end_match.group(1))
        else:
            page_end = page_start

        level = _determine_level(sec_num)
        parent = _get_parent_number(sec_num)
        path = _build_section_path(sec_num, path_map)
        path_map[sec_num] = path

        # Extract footnotes from section text
        body, footnotes = _extract_footnotes(section_text)
        refs = detect_circular_references(section_text)

        # Gather tables from pages in range
        tables = []
        for page in doc.pages:
            if page_start <= page.page_num <= page_end:
                tables.extend(page.tables)

        sections.append(
            DetectedSection(
                section_number=sec_num,
                section_title=sec_title,
                section_path=path,
                parent_section_number=parent,
                page_start=page_start,
                page_end=page_end,
                text=body,
                tables=tables,
                footnotes=footnotes,
                references=refs,
                level=level,
            )
        )

    logger.info(f"Detected {len(sections)} sections in {doc.filename}")
    return sections
