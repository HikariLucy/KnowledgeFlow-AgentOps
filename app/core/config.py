"""Centralized application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and environment variables."""

    # Application Info
    app_name: str = "KnowledgeFlow RAG"
    app_env: str = "development"

    # LLM Provider (Google Gemini)
    gemini_api_key: Optional[str] = None
    gemini_router_model: str = "gemini-3.5-flash-lite"
    gemini_chat_model: str = "gemini-3.5-flash"
    gemini_embedding_model: str = "gemini-embedding-2"

    # Document Chunking Defaults
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Vector Store & Retrieval Defaults
    embedding_dimension: int = 768
    retrieval_top_k: int = 4
    vectorstore_dir: str = "vectorstore"

    # RAG Generation & Abstention Defaults (Phase 3)
    # Note: 0.60 is an experimental threshold to be calibrated with in-domain and out-of-domain queries
    rag_min_similarity: float = 0.60
    llm_temperature: Optional[float] = 1.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def validate_parameters(self) -> "Settings":
        """Validate chunk, retrieval and generation configuration parameters."""
        if self.chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {self.chunk_size}")
        if self.chunk_overlap < 0:
            raise ValueError(
                f"chunk_overlap must be non-negative, got {self.chunk_overlap}"
            )
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be strictly less than chunk_size ({self.chunk_size})"
            )
        if self.embedding_dimension <= 0:
            raise ValueError(
                f"embedding_dimension must be positive, got {self.embedding_dimension}"
            )
        if self.retrieval_top_k <= 0:
            raise ValueError(
                f"retrieval_top_k must be positive, got {self.retrieval_top_k}"
            )
        if not (0.0 <= self.rag_min_similarity <= 1.0):
            raise ValueError(
                f"rag_min_similarity must be between 0.0 and 1.0, got {self.rag_min_similarity}"
            )
        if self.llm_temperature is not None and not (
            0.0 <= self.llm_temperature <= 2.0
        ):
            raise ValueError(
                f"llm_temperature must be between 0.0 and 2.0, got {self.llm_temperature}"
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()
