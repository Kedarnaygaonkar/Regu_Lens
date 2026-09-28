"""
ReguLens Configuration
Loads and validates all environment variables at startup.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # MongoDB
    mongodb_uri: str
    mongodb_database: str = "ReguLens"

    # Embedding
    embedding_provider: Literal["openai", "gemini", "cohere", "local"] = "gemini"
    embedding_model: str = "models/gemini-embedding-001"
    embedding_dimensions: int = 3072
    embedding_api_key: str = ""

    # LLM
    llm_provider: Literal["openai", "gemini", "anthropic"] = "gemini"
    llm_model: str = "gemini-2.5-flash"
    llm_api_key: str = ""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # Chunking
    naive_chunk_size: int = 512
    naive_chunk_overlap: int = 64
    structure_aware_max_chunk_size: int = 1024

    # Uploads directory
    upload_dir: str = "uploads"

    @field_validator("mongodb_uri")
    @classmethod
    def validate_mongo_uri(cls, v: str) -> str:
        if not v or v.startswith("mongodb+srv://<user>"):
            raise ValueError("MONGODB_URI must be set to a valid connection string")
        return v

    @model_validator(mode="after")
    def validate_api_keys(self) -> "Settings":
        # Warn but don't block startup — keys are only needed at query time
        if not self.embedding_api_key and self.embedding_provider != "local":
            import warnings
            warnings.warn(
                f"EMBEDDING_API_KEY is empty (provider={self.embedding_provider}). "
                "Embedding calls will fail."
            )
        if not self.llm_api_key:
            import warnings
            warnings.warn(
                f"LLM_API_KEY is empty (provider={self.llm_provider}). "
                "LLM calls will fail."
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
