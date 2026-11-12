"""Offline unit tests for RAG Context Building and Citation Validation."""

from langchain_core.documents import Document
import pytest

from app.rag.context import (
    build_rag_context,
    extract_citations_from_text,
    validate_citations,
)
from app.rag.schemas import SearchResult


@pytest.fixture
def sample_search_results():
    """Fixture providing a list of 3 ranked SearchResult objects."""
    return [
        SearchResult(
            document=Document(
                page_content="Política de gestión de contraseñas de 12 caracteres.",
                metadata={
                    "source": "knowledge/internal/passwords.md",
                    "source_type": "internal",
                    "file_name": "passwords.md",
                    "chunk_index": 0,
                },
            ),
            score=0.8850,
            rank=1,
        ),
        SearchResult(
            document=Document(
                page_content="Procedimiento de rotación de credenciales cada 90 días.",
                metadata={
                    "source": "knowledge/internal/passwords.md",
                    "source_type": "internal",
                    "file_name": "passwords.md",
                    "chunk_index": 1,
                },
            ),
            score=0.7640,
            rank=2,
        ),
        SearchResult(
            document=Document(
                page_content="Estándares NIST SP 800-63B de verificación de identidad digital.",
                metadata={
                    "source": "knowledge/external/nist.txt",
                    "source_type": "external",
                    "file_name": "nist.txt",
                    "chunk_index": 0,
                },
            ),
            score=0.6920,
            rank=3,
        ),
    ]


def test_build_rag_context_ids_and_metadata(sample_search_results):
    """Verify build_rag_context creates S1..SN IDs and preserves all metadata fields."""
    context_str, sources = build_rag_context(sample_search_results)

    assert "[S1]" in context_str
    assert "[S2]" in context_str
    assert "[S3]" in context_str

    assert len(sources) == 3
    assert sources[0].id == "S1"
    assert sources[0].file_name == "passwords.md"
    assert sources[0].source_type == "internal"
    assert sources[0].chunk_index == 0
    assert sources[0].score == 0.8850

    assert sources[2].id == "S3"
    assert sources[2].file_name == "nist.txt"
    assert sources[2].source_type == "external"


def test_build_rag_context_empty():
    """Verify build_rag_context handles empty input list."""
    context_str, sources = build_rag_context([])
    assert context_str == ""
    assert sources == []


def test_extract_citations():
    """Verify citation extraction regex finds all citations and deduplicates."""
    text = "Las contraseñas deben ser de 12 caracteres [S1]. Deben rotar cada 90 días [S2] según la política [S1]."
    citations = extract_citations_from_text(text)
    assert citations == ["S1", "S2"]


def test_validate_citations_valid_set():
    """Verify validate_citations approves text containing only valid citation IDs."""
    valid_ids = {"S1", "S2", "S3"}
    text = "Información respaldada en [S1] y complementada por [S3]."
    is_valid, valids, phantoms = validate_citations(text, valid_ids)

    assert is_valid is True
    assert valids == ["S1", "S3"]
    assert phantoms == []


def test_validate_citations_detects_phantom_citations():
    """Verify validate_citations detects and invalidates phantom citations."""
    valid_ids = {"S1", "S2"}
    text = "Afirmación fundamentada en [S1] pero con cita fantasma [S7] e inventada [S9]."
    is_valid, valids, phantoms = validate_citations(text, valid_ids)

    assert is_valid is False
    assert valids == ["S1"]
    assert phantoms == ["S7", "S9"]


def test_validate_citations_zero_citations_invalid_when_sources_exist():
    """Verify validate_citations fails if response lacks citations while sources exist."""
    valid_ids = {"S1", "S2"}
    text = "Respuesta sin ninguna cita documental."
    is_valid, valids, phantoms = validate_citations(text, valid_ids)

    assert is_valid is False
    assert valids == []
    assert phantoms == []


def test_validate_citations_zero_citations_valid_when_sources_empty():
    """Verify validate_citations passes with zero citations when valid_source_ids is empty."""
    valid_ids = set()
    text = "No encontré evidencia suficiente en las fuentes disponibles."
    is_valid, valids, phantoms = validate_citations(text, valid_ids)

    assert is_valid is True
    assert valids == []
    assert phantoms == []
