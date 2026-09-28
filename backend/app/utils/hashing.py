"""Hashing utilities for content deduplication."""
from __future__ import annotations

import hashlib
import re
import unicodedata


def sha256_hash(text: str) -> str:
    """Return SHA-256 hex digest of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha256(path: str) -> str:
    """Return SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_text(text: str) -> str:
    """Normalize whitespace and unicode for consistent hashing."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def canonical_hash(text: str) -> str:
    """Hash of normalized text — for near-duplicate detection."""
    return sha256_hash(normalize_text(text))
