"""Offline unit tests for RAG Generator and citation validation/repair."""

from unittest.mock import MagicMock
import pytest

from app.rag.generator import FakeRAGGenerator, GeminiRAGGenerator
from app.rag.schemas import SourceReference


@pytest.fixture
def sample_source_refs():
    """Fixture providing sample SourceReferences [S1, S2]."""
    return [
        SourceReference(
            id="S1",
            file_name="seguridad.md",
            source_type="internal",
            chunk_index=0,
            score=0.85,
        ),
        SourceReference(
            id="S2",
            file_name="owasp.md",
            source_type="external",
            chunk_index=0,
            score=0.78,
        ),
    ]


def test_fake_rag_generator_grounded(sample_source_refs):
    """Verify FakeRAGGenerator produces grounded text with valid citations."""
    generator = FakeRAGGenerator()
    answer, citations, is_grounded = generator.generate(
        query="¿Cómo reportar un incidente?",
        context_str="[S1]...",
        source_references=sample_source_refs,
    )

    assert is_grounded is True
    assert citations == ["S1"]
    assert "[S1]" in answer


def test_fake_rag_generator_phantom_citation_rejection(sample_source_refs):
    """Verify generator flags is_grounded=False when phantom citations are present."""
    generator = FakeRAGGenerator(force_phantom_citation=True)
    answer, citations, is_grounded = generator.generate(
        query="test",
        context_str="[S1]...",
        source_references=sample_source_refs,
    )

    assert is_grounded is False
    assert citations == []


def test_gemini_rag_generator_valid_citation(sample_source_refs):
    """Verify GeminiRAGGenerator accepts valid citations on first try."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_sdk = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "De acuerdo a la política interna, los accesos deben solicitarse vía ticket [S1]."
    mock_sdk.models.generate_content.return_value = mock_resp
    mock_client.get_client.return_value = mock_sdk

    generator = GeminiRAGGenerator(gemini_client=mock_client)
    answer, citations, is_grounded = generator.generate(
        query="¿Cómo solicitar accesos?",
        context_str="[S1]...",
        source_references=sample_source_refs,
    )

    assert is_grounded is True
    assert citations == ["S1"]
    assert "[S1]" in answer


def test_gemini_rag_generator_repair_success(sample_source_refs):
    """Verify GeminiRAGGenerator attempts 1 repair when phantom citations exist and succeeds."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_sdk = MagicMock()

    # Attempt 1: contains invalid citation [S7]
    resp1 = MagicMock()
    resp1.text = "Respuesta con cita inválida [S7]."

    # Attempt 2 (repair): contains valid citation [S1]
    resp2 = MagicMock()
    resp2.text = "Respuesta corregida con cita válida [S1]."

    mock_sdk.models.generate_content.side_effect = [resp1, resp2]
    mock_client.get_client.return_value = mock_sdk

    generator = GeminiRAGGenerator(gemini_client=mock_client)
    answer, citations, is_grounded = generator.generate(
        query="Pregunta de prueba",
        context_str="[S1]...",
        source_references=sample_source_refs,
    )

    assert is_grounded is True
    assert citations == ["S1"]
    assert "Respuesta corregida" in answer


def test_gemini_rag_generator_repair_failure_fallback(sample_source_refs):
    """Verify GeminiRAGGenerator returns safe fallback when repair still contains phantom citations."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_sdk = MagicMock()

    # Attempt 1: invalid citation [S7]
    resp1 = MagicMock()
    resp1.text = "Respuesta con cita [S7]."

    # Attempt 2: still invalid citation [S8]
    resp2 = MagicMock()
    resp2.text = "Respuesta aún con cita [S8]."

    mock_sdk.models.generate_content.side_effect = [resp1, resp2]
    mock_client.get_client.return_value = mock_sdk

    generator = GeminiRAGGenerator(gemini_client=mock_client)
    answer, citations, is_grounded = generator.generate(
        query="Pregunta de prueba",
        context_str="[S1]...",
        source_references=sample_source_refs,
    )

    assert is_grounded is False
    assert citations == []
    assert "No fue posible generar una respuesta con trazabilidad verificable" in answer


def test_gemini_rag_generator_zero_citations_repair_success(sample_source_refs):
    """Verify GeminiRAGGenerator repairs a response that initially contained zero citations."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_sdk = MagicMock()

    # Attempt 1: zero citations
    resp1 = MagicMock()
    resp1.text = "Respuesta sin citas documentales."

    # Attempt 2: repair adds valid citation [S1]
    resp2 = MagicMock()
    resp2.text = "Respuesta reparada con cita documental válida [S1]."

    mock_sdk.models.generate_content.side_effect = [resp1, resp2]
    mock_client.get_client.return_value = mock_sdk

    generator = GeminiRAGGenerator(gemini_client=mock_client)
    answer, citations, is_grounded = generator.generate(
        query="Pregunta de prueba",
        context_str="[S1]...",
        source_references=sample_source_refs,
    )

    assert is_grounded is True
    assert citations == ["S1"]
    assert "[S1]" in answer


def test_gemini_rag_generator_zero_citations_repair_failure_fallback(sample_source_refs):
    """Verify GeminiRAGGenerator falls back safely when repair continues to lack citations."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_sdk = MagicMock()

    # Attempt 1: zero citations
    resp1 = MagicMock()
    resp1.text = "Respuesta sin citas."

    # Attempt 2: still zero citations
    resp2 = MagicMock()
    resp2.text = "Respuesta aún sin citas."

    mock_sdk.models.generate_content.side_effect = [resp1, resp2]
    mock_client.get_client.return_value = mock_sdk

    generator = GeminiRAGGenerator(gemini_client=mock_client)
    answer, citations, is_grounded = generator.generate(
        query="Pregunta de prueba",
        context_str="[S1]...",
        source_references=sample_source_refs,
    )

    assert is_grounded is False
    assert citations == []
    assert "No fue posible generar una respuesta con trazabilidad verificable" in answer
