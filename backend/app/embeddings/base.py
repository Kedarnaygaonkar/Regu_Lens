"""
Abstract embedding provider interface for ReguLens.

Supports:
  - OpenAI
  - Google Gemini
  - Cohere (stub)
  - Local/mock (for testing)

Implements:
  - Batch embedding with retry
  - Content-hash based caching
  - Model/version tracking
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts. Returns list of embedding vectors."""
        ...

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Embed a single query string."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensions."""
        ...

    def _retry(self, fn, max_attempts: int = 3, delay: float = 1.0):
        """Generic retry wrapper."""
        for attempt in range(max_attempts):
            try:
                return fn()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                wait = delay * (2 ** attempt)
                logger.warning(f"Embedding attempt {attempt + 1} failed: {e}. Retrying in {wait}s…")
                time.sleep(wait)
