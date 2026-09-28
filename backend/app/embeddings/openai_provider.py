"""OpenAI embedding provider for ReguLens."""
from __future__ import annotations

import logging
from typing import List

from app.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)

# Batch size limit for OpenAI API
OPENAI_BATCH_SIZE = 100


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI text-embedding-3-small / text-embedding-3-large provider.
    """

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        self._client = OpenAI(api_key=api_key)
        self._model = model
        # Dimension map
        self._dims = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }.get(model, 1536)

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dims

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed texts in batches, returning list of vectors."""
        if not texts:
            return []

        all_embeddings = []

        for i in range(0, len(texts), OPENAI_BATCH_SIZE):
            batch = texts[i : i + OPENAI_BATCH_SIZE]
            # Strip empty texts
            batch = [t.strip() or " " for t in batch]

            def _call(b=batch):
                response = self._client.embeddings.create(model=self._model, input=b)
                return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]

            embeddings = self._retry(_call)
            all_embeddings.extend(embeddings)
            logger.debug(f"Embedded batch {i // OPENAI_BATCH_SIZE + 1}: {len(batch)} texts")

        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        query = query.strip() or " "

        def _call():
            response = self._client.embeddings.create(model=self._model, input=[query])
            return response.data[0].embedding

        return self._retry(_call)
