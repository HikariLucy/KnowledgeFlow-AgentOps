"""Offline unit tests for document/query embedding preparation and provider contracts."""

import pytest
from langchain_core.documents import Document

from app.rag.embeddings import (
    DeterministicFakeEmbeddings,
    GeminiEmbeddings,
    get_document_title,
    prepare_document_for_embedding,
    prepare_query_for_embedding,
)


def test_prepare_document_with_title():
    """Verify document preparation when metadata contains a title."""
    meta = {"title": "Guía de Seguridad", "file_name": "seguridad.md"}
    result = prepare_document_for_embedding("Contenido de prueba", meta)
    assert result == "title: Guía de Seguridad | text: Contenido de prueba"


def test_prepare_document_fallback_to_file_name():
    """Verify title fallback uses file_name when title is missing or empty."""
    meta = {"file_name": "normativa.txt"}
    result = prepare_document_for_embedding("Reglamento interno", meta)
    assert result == "title: normativa.txt | text: Reglamento interno"

    meta_empty_title = {"title": "   ", "file_name": "documento.pdf"}
    result_empty = prepare_document_for_embedding(
        "Texto", meta_empty_title
    )
    assert result_empty == "title: documento.pdf | text: Texto"


def test_prepare_document_fallback_to_none():
    """Verify title fallback uses 'none' when neither title nor file_name is present."""
    result = prepare_document_for_embedding("Texto sin metadata", {})
    assert result == "title: none | text: Texto sin metadata"

    result_none_meta = prepare_document_for_embedding("Texto sin metadata", None)
    assert result_none_meta == "title: none | text: Texto sin metadata"


def test_prepare_query_format():
    """Verify search query preparation follows 'task: search result | query: {query}'."""
    query = "¿Cómo reportar un incidente?"
    result = prepare_query_for_embedding(query)
    assert result == "task: search result | query: ¿Cómo reportar un incidente?"


def test_prepare_document_empty_content_raises():
    """Verify empty or whitespace-only content raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        prepare_document_for_embedding("", {"file_name": "test.txt"})

    with pytest.raises(ValueError, match="cannot be empty"):
        prepare_document_for_embedding("   \n\t  ", {"file_name": "test.txt"})


def test_prepare_query_empty_raises():
    """Verify empty or whitespace-only query raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        prepare_query_for_embedding("")

    with pytest.raises(ValueError, match="cannot be empty"):
        prepare_query_for_embedding("   ")


def test_fake_embeddings_dimension_contract():
    """Verify DeterministicFakeEmbeddings respects the configured dimension."""
    dim = 768
    provider = DeterministicFakeEmbeddings(embedding_dimension=dim)
    vec = provider.embed_query("Prueba de consulta")
    assert len(vec) == dim
    assert isinstance(vec[0], float)


def test_fake_embeddings_invalid_dimension_raises():
    """Verify non-positive dimension raises ValueError."""
    with pytest.raises(ValueError, match="positive"):
        DeterministicFakeEmbeddings(embedding_dimension=0)

    with pytest.raises(ValueError, match="positive"):
        DeterministicFakeEmbeddings(embedding_dimension=-10)


def test_fake_embeddings_cardinality_contract():
    """Verify N documents produce exactly N embeddings (1 chunk -> 1 vector)."""
    provider = DeterministicFakeEmbeddings(embedding_dimension=768)
    docs = [
        Document(
            page_content=f"Chunk número {i}",
            metadata={"source": f"doc_{i}.md", "file_name": f"doc_{i}.md"},
        )
        for i in range(10)
    ]

    embeddings = provider.embed_documents(docs)
    assert len(embeddings) == len(docs)
    for vec in embeddings:
        assert len(vec) == 768


def test_fake_embeddings_empty_documents_list():
    """Verify empty input documents returns empty list."""
    provider = DeterministicFakeEmbeddings(embedding_dimension=768)
    embeddings = provider.embed_documents([])
    assert embeddings == []


def test_fake_embeddings_deterministic():
    """Verify same text produces identical embedding vectors."""
    provider = DeterministicFakeEmbeddings(embedding_dimension=768)
    vec1 = provider.embed_query("Consulta idéntica")
    vec2 = provider.embed_query("Consulta idéntica")
    assert vec1 == vec2


def test_document_immutability():
    """Verify embedding generation does not mutate original Document content or metadata."""
    provider = DeterministicFakeEmbeddings(embedding_dimension=768)
    orig_meta = {"source": "test.md", "file_name": "test.md", "source_type": "internal"}
    doc = Document(page_content="Texto intacto", metadata=orig_meta.copy())

    provider.embed_document(doc)

    assert doc.page_content == "Texto intacto"
    assert doc.metadata == orig_meta
