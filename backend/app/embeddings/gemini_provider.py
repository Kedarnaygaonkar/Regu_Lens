"""Google Gemini embedding provider for ReguLens."""
from __future__ import annotations

import logging
import time
from typing import List

from app.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)

GEMINI_BATCH_SIZE = 100


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Google Gemini embedding provider.
    Uses models/gemini-embedding-001 (3072 dimensions) or other specified Gemini embedding model.
    """

    def __init__(self, api_key: str, model: str = "models/gemini-embedding-001", dimensions: int = 3072):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai package not installed.")

        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai
        self._model = model
        self._dims = dimensions or 3072

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dims

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        all_embeddings = []
        for i in range(0, len(texts), GEMINI_BATCH_SIZE):
            batch = texts[i : i + GEMINI_BATCH_SIZE]

            def _call(b=batch):
                result = self._genai.embed_content(
                    model=self._model,
                    content=b,
                    task_type="retrieval_document",
                )
                return result["embedding"] if len(b) == 1 else result["embedding"]

            embeddings = self._retry(_call)
            if isinstance(embeddings[0], float):
                # Single text returned as flat vector
                all_embeddings.append(embeddings)
            else:
                all_embeddings.extend(embeddings)

        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        def _call():
            result = self._genai.embed_content(
                model=self._model,
                content=query,
                task_type="retrieval_query",
            )
            return result["embedding"]

        return self._retry(_call)


class LocalMockEmbeddingProvider(EmbeddingProvider):
    """
    Mock embedding provider for testing without API keys.
    Returns random unit vectors.
    """

    def __init__(self, dimensions: int = 1536):
        import numpy as np
        self._dims = dimensions
        self._np = np

    @property
    def model_name(self) -> str:
        return "mock-embedding-v1"

    @property
    def dimensions(self) -> int:
        return self._dims

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            # Deterministic hash-based vector for reproducibility
            seed = hash(text) % (2**32)
            rng = self._np.random.RandomState(seed)
            vec = rng.randn(self._dims).astype(float)
            vec = vec / (self._np.linalg.norm(vec) + 1e-9)
            embeddings.append(vec.tolist())
        return embeddings

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]
