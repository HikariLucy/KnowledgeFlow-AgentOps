"""Tests for document chunking and metadata preservation."""

import pytest
from langchain_core.documents import Document

from app.rag.chunking import split_documents, validate_chunking_parameters


def test_validate_chunking_parameters_valid():
    """Verify valid chunking parameters pass without error."""
    validate_chunking_parameters(chunk_size=500, chunk_overlap=50)
    validate_chunking_parameters(chunk_size=100, chunk_overlap=0)


def test_validate_chunking_parameters_overlap_equal_or_greater():
    """Verify ValueError is raised when chunk_overlap >= chunk_size."""
    with pytest.raises(ValueError, match="strictly less than"):
        validate_chunking_parameters(chunk_size=100, chunk_overlap=100)

    with pytest.raises(ValueError, match="strictly less than"):
        validate_chunking_parameters(chunk_size=100, chunk_overlap=150)


def test_validate_chunking_parameters_negative():
    """Verify ValueError is raised for negative or non-positive chunk_size or chunk_overlap."""
    with pytest.raises(ValueError, match="greater than 0"):
        validate_chunking_parameters(chunk_size=0, chunk_overlap=0)

    with pytest.raises(ValueError, match="non-negative"):
        validate_chunking_parameters(chunk_size=100, chunk_overlap=-10)


def test_split_documents_preserves_metadata():
    """Verify chunks preserve original metadata and include chunk_index."""
    long_content = (
        "Sección 1: Introducción a la arquitectura de sistemas distribuidos.\n\n"
        "Sección 2: Protocolos de comunicación y mensajería orientada a eventos.\n\n"
        "Sección 3: Estrategias de particionamiento, sharding y replicación de datos.\n\n"
        "Sección 4: Mecanismos de tolerancia a fallos y recuperación ante desastres."
    )

    doc = Document(
        page_content=long_content,
        metadata={
            "source": "knowledge/internal/manual_arquitectura.md",
            "source_type": "internal",
            "file_name": "manual_arquitectura.md",
            "file_extension": ".md",
        },
    )

    # Use small chunk_size to force multiple chunks
    chunks = split_documents([doc], chunk_size=100, chunk_overlap=20)

    assert len(chunks) > 1

    for idx, chunk in enumerate(chunks):
        assert chunk.metadata["source"] == "knowledge/internal/manual_arquitectura.md"
        assert chunk.metadata["source_type"] == "internal"
        assert chunk.metadata["file_name"] == "manual_arquitectura.md"
        assert chunk.metadata["file_extension"] == ".md"
        assert chunk.metadata["chunk_index"] == idx
        assert len(chunk.page_content) > 0


def test_split_documents_external_source_type_preserved():
    """Verify external source_type is strictly preserved across chunks."""
    doc = Document(
        page_content="Normativa externa sobre estándares de interoperabilidad y seguridad.",
        metadata={
            "source": "knowledge/external/normativa.txt",
            "source_type": "external",
            "file_name": "normativa.txt",
            "file_extension": ".txt",
        },
    )

    chunks = split_documents([doc], chunk_size=50, chunk_overlap=10)

    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.metadata["source_type"] == "external"
        assert chunk.metadata["source"] == "knowledge/external/normativa.txt"


def test_split_empty_document_list():
    """Verify empty document list returns empty list."""
    chunks = split_documents([])
    assert chunks == []


def test_split_rejects_invalid_overlap_in_function():
    """Verify split_documents rejects invalid chunk_overlap >= chunk_size."""
    doc = Document(page_content="Texto de prueba", metadata={"source": "test.md"})
    with pytest.raises(ValueError):
        split_documents([doc], chunk_size=100, chunk_overlap=100)


def test_split_empty_document_content():
    """Verify Document with empty page_content produces no chunks."""
    doc = Document(page_content="", metadata={"source": "empty.md"})
    chunks = split_documents([doc], chunk_size=100, chunk_overlap=10)
    assert chunks == []


def test_split_whitespace_only_document_content():
    """Verify Document with only whitespace page_content produces no chunks."""
    doc = Document(page_content="   \n\t  \n  ", metadata={"source": "spaces.md"})
    chunks = split_documents([doc], chunk_size=100, chunk_overlap=10)
    assert chunks == []


def test_split_mixed_valid_and_empty_documents():
    """Verify only valid non-empty documents produce chunks in a mixed collection."""
    doc1 = Document(page_content="   \n  ", metadata={"source": "empty1.md"})
    doc2 = Document(page_content="Texto válido con información.", metadata={"source": "valid.md", "source_type": "internal"})
    doc3 = Document(page_content="", metadata={"source": "empty2.md"})

    chunks = split_documents([doc1, doc2, doc3], chunk_size=100, chunk_overlap=10)
    assert len(chunks) == 1
    assert chunks[0].metadata["source"] == "valid.md"
    assert chunks[0].page_content == "Texto válido con información."


def test_settings_validation_invalid_chunk_overlap():
    """Verify Settings rejects chunk_overlap >= chunk_size."""
    from app.core.config import Settings

    with pytest.raises(ValueError, match="strictly less than"):
        Settings(chunk_size=200, chunk_overlap=200)

    with pytest.raises(ValueError, match="strictly less than"):
        Settings(chunk_size=200, chunk_overlap=250)
