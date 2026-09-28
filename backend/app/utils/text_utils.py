"""Text utilities for ReguLens."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple


# ─── Section heading patterns for Indian regulatory documents ─────────────────
HEADING_PATTERNS = [
    # "1.", "1.2", "1.2.3", "1.2.3.4" followed by uppercase or title-case text
    re.compile(r"^(\d+(?:\.\d+)*)\s+([A-Z][^\n]{3,})$", re.MULTILINE),
    # Roman numerals: "I.", "II.", etc.
    re.compile(r"^([IVXivx]+\.)\s+([A-Z][^\n]{3,})$", re.MULTILINE),
    # Part / Chapter / Section headers
    re.compile(r"^(PART|CHAPTER|SECTION|ANNEX(?:URE)?|SCHEDULE)\s+([A-Z0-9]+)", re.MULTILINE | re.IGNORECASE),
    # Alphabetic: "A.", "B.", etc.
    re.compile(r"^([A-Z]\.)\s+([A-Z][^\n]{3,})$", re.MULTILINE),
]

# Supersession language patterns
SUPERSESSION_PATTERNS = [
    re.compile(r"supersed(?:es|ed|ing)", re.IGNORECASE),
    re.compile(r"replac(?:es|ed|ing)", re.IGNORECASE),
    re.compile(r"withdraw(?:s|n|al)?", re.IGNORECASE),
    re.compile(r"amend(?:s|ed|ment)", re.IGNORECASE),
    re.compile(r"in\s+supersession\s+of", re.IGNORECASE),
    re.compile(r"in\s+partial\s+modification\s+of", re.IGNORECASE),
    re.compile(r"stand(?:s)?\s+cancelled", re.IGNORECASE),
    re.compile(r"stand(?:s)?\s+rescinded", re.IGNORECASE),
    re.compile(r"consolidat(?:es|ed|ing)", re.IGNORECASE),
]

CIRCULAR_REF_PATTERN = re.compile(
    r"(?:RBI|SEBI|IRDAI|PFRDA)\s*/\s*[\w\.]+\s*/\s*[\w\.]+\s*/\s*\d+",
    re.IGNORECASE,
)


def detect_headings(text: str) -> List[Tuple[str, str, int]]:
    """
    Return list of (section_number, section_title, char_offset) tuples
    for detected headings.
    """
    headings = []
    for pattern in HEADING_PATTERNS:
        for m in pattern.finditer(text):
            num = m.group(1).strip()
            title = m.group(2).strip() if m.lastindex >= 2 else ""
            headings.append((num, title, m.start()))
    # Deduplicate and sort by offset
    seen = set()
    unique = []
    for h in sorted(headings, key=lambda x: x[2]):
        key = (h[0], h[2])
        if key not in seen:
            seen.add(key)
            unique.append(h)
    return unique


def detect_supersession_language(text: str) -> List[str]:
    """Return list of matching supersession phrases found in text."""
    found = []
    for pat in SUPERSESSION_PATTERNS:
        for m in pat.finditer(text):
            # Return surrounding sentence context
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 200)
            snippet = text[start:end].replace("\n", " ").strip()
            found.append(snippet)
    return found


def detect_circular_references(text: str) -> List[str]:
    """Return list of circular reference strings (e.g., RBI/2019-20/123)."""
    return list(set(CIRCULAR_REF_PATTERN.findall(text)))


def split_into_sentences(text: str) -> List[str]:
    """Naive sentence splitter for regulatory text."""
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    return [s.strip() for s in sentences if s.strip()]


def count_tokens_approx(text: str, chars_per_token: int = 4) -> int:
    """Approximate token count for text (conservative estimate)."""
    return len(text) // chars_per_token


def truncate_text(text: str, max_chars: int = 2000, suffix: str = "…") -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars - len(suffix)] + suffix


def clean_extracted_text(text: str) -> str:
    """Clean PDF-extracted text: remove hyphenation, normalize whitespace."""
    # Remove PDF hyphenation at line ends
    text = re.sub(r"-\n(\w)", r"\1", text)
    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    # Remove excessive blank lines but preserve paragraph breaks
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
