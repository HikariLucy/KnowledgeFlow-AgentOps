"""Tests for configuration and decoupled LLM client."""

import pytest
from app.core.config import Settings
from app.llm.client import GeminiClient


def test_settings_defaults():
    """Verify default configuration settings."""
    settings = Settings(
        app_name="KnowledgeFlow RAG",
        chunk_size=500,
        chunk_overlap=50,
    )
    assert settings.app_name == "KnowledgeFlow RAG"
    assert settings.chunk_size == 500
    assert settings.chunk_overlap == 50
    assert settings.embedding_dimension == 768
    assert settings.retrieval_top_k == 4
    assert settings.rag_min_similarity == 0.60
    assert settings.llm_temperature == 1.0
    assert settings.vectorstore_dir == "vectorstore"
    assert settings.gemini_chat_model == "gemini-3.5-flash"
    assert settings.gemini_embedding_model == "gemini-embedding-2"


def test_settings_validation_invalid_rag_min_similarity():
    """Verify out-of-range rag_min_similarity raises ValueError."""
    with pytest.raises(ValueError, match="rag_min_similarity"):
        Settings(rag_min_similarity=-0.1)

    with pytest.raises(ValueError, match="rag_min_similarity"):
        Settings(rag_min_similarity=1.5)


def test_settings_validation_invalid_llm_temperature():
    """Verify out-of-range llm_temperature raises ValueError."""
    with pytest.raises(ValueError, match="llm_temperature"):
        Settings(llm_temperature=-0.5)

    with pytest.raises(ValueError, match="llm_temperature"):
        Settings(llm_temperature=3.0)


def test_settings_validation_invalid_embedding_dimension():
    """Verify non-positive embedding dimension raises ValueError."""
    with pytest.raises(ValueError, match="embedding_dimension must be positive"):
        Settings(embedding_dimension=0)

    with pytest.raises(ValueError, match="embedding_dimension must be positive"):
        Settings(embedding_dimension=-100)


def test_settings_validation_invalid_retrieval_top_k():
    """Verify non-positive retrieval_top_k raises ValueError."""
    with pytest.raises(ValueError, match="retrieval_top_k must be positive"):
        Settings(retrieval_top_k=0)

    with pytest.raises(ValueError, match="retrieval_top_k must be positive"):
        Settings(retrieval_top_k=-2)


def test_gemini_client_unconfigured():
    """Verify GeminiClient behaves safely when API key is missing."""
    settings = Settings(gemini_api_key=None)
    client = GeminiClient(settings=settings)

    assert client.is_configured is False
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not configured"):
        client.get_client()


def test_gemini_client_configured_property():
    """Verify is_configured returns True when key is set."""
    settings = Settings(gemini_api_key="demo-test-api-key")
    client = GeminiClient(settings=settings)

    assert client.is_configured is True
