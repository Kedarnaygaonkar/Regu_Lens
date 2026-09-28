"""Embeddings package — factory and providers."""
from app.embeddings.base import EmbeddingProvider
from app.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.embeddings.gemini_provider import GeminiEmbeddingProvider, LocalMockEmbeddingProvider


def get_embedding_provider(
    provider: str = "openai",
    api_key: str = "",
    model: str = "",
    dimensions: int = 1536,
) -> EmbeddingProvider:
    """
    Factory function to create the configured embedding provider.
    
    Args:
        provider: "openai" | "gemini" | "local"
        api_key: API key (not needed for "local")
        model: Model name override
        dimensions: Dimensions (used for "local")
    """
    provider = provider.lower().strip()

    if provider == "openai":
        m = model or "text-embedding-3-small"
        return OpenAIEmbeddingProvider(api_key=api_key, model=m)
    elif provider == "gemini":
        m = model or "models/gemini-embedding-001"
        dims = dimensions if dimensions and dimensions != 1536 else 3072
        return GeminiEmbeddingProvider(api_key=api_key, model=m, dimensions=dims)
    elif provider == "local":
        return LocalMockEmbeddingProvider(dimensions=dimensions)
    else:
        raise ValueError(f"Unknown embedding provider: {provider!r}. Choose from: openai, gemini, local")


__all__ = [
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "GeminiEmbeddingProvider",
    "LocalMockEmbeddingProvider",
    "get_embedding_provider",
]
