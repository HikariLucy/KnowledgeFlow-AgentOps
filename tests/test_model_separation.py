"""Offline unit tests for Source Router and Generation Model separation."""

from unittest.mock import MagicMock
from app.core.config import Settings
from app.agents.source_router import GeminiSourceRouter
from app.rag.generator import GeminiRAGGenerator
from app.rag.schemas import SourceReference
from app.evaluation.schemas import (
    EvaluationRunMetadata,
    EvaluationReport,
    RouterSummaryMetrics,
    RetrievalSummaryMetrics,
    AbstentionSummaryMetrics,
    CitationAndGenerationSummaryMetrics,
)
from app.evaluation.reporter import generate_markdown_summary


def test_settings_exposes_gemini_router_model():
    """Verify Settings has gemini_router_model separate from gemini_chat_model."""
    settings = Settings(
        gemini_router_model="gemini-custom-router",
        gemini_chat_model="gemini-custom-chat",
        gemini_embedding_model="gemini-custom-embedding",
    )
    assert settings.gemini_router_model == "gemini-custom-router"
    assert settings.gemini_chat_model == "gemini-custom-chat"
    assert settings.gemini_embedding_model == "gemini-custom-embedding"


def test_gemini_source_router_uses_gemini_router_model():
    """Verify GeminiSourceRouter calls generate_content with gemini_router_model, NOT gemini_chat_model."""
    settings = Settings(
        gemini_router_model="gemini-3.5-flash-lite",
        gemini_chat_model="gemini-3.5-flash",
    )
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"source_scope": "internal", "confidence": 0.95, "routing_reason": "test"}'
    mock_sdk_client.models.generate_content.return_value = mock_response
    mock_client.get_client.return_value = mock_sdk_client

    router = GeminiSourceRouter(gemini_client=mock_client, settings=settings)
    decision = router.route("Consulta interna")

    assert decision.source_scope == "internal"
    mock_sdk_client.models.generate_content.assert_called_once()
    call_kwargs = mock_sdk_client.models.generate_content.call_args[1]
    assert call_kwargs["model"] == "gemini-3.5-flash-lite"
    assert call_kwargs["model"] != "gemini-3.5-flash"


def test_gemini_rag_generator_uses_gemini_chat_model():
    """Verify GeminiRAGGenerator calls generate_content with gemini_chat_model."""
    settings = Settings(
        gemini_router_model="gemini-3.5-flash-lite",
        gemini_chat_model="gemini-3.5-flash",
    )
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Esta es la respuesta fundamentada [S1]."
    mock_sdk_client.models.generate_content.return_value = mock_response
    mock_client.get_client.return_value = mock_sdk_client

    generator = GeminiRAGGenerator(gemini_client=mock_client, settings=settings)
    source_ref = SourceReference(
        id="S1",
        file_name="doc.txt",
        source_type="internal",
        chunk_index=0,
        score=0.9,
    )
    answer, citations, is_grounded = generator.generate(
        query="¿Pregunta?",
        context_str="[S1] Contenido...",
        source_references=[source_ref],
    )

    assert is_grounded is True
    assert "[S1]" in answer
    mock_sdk_client.models.generate_content.assert_called_once()
    call_kwargs = mock_sdk_client.models.generate_content.call_args[1]
    assert call_kwargs["model"] == "gemini-3.5-flash"
    assert call_kwargs["model"] != "gemini-3.5-flash-lite"


def test_evaluation_run_metadata_contains_router_model():
    """Verify EvaluationRunMetadata contains router_model field."""
    meta = EvaluationRunMetadata(
        timestamp="2026-09-01T12:00:00Z",
        git_commit="abcdef0",
        git_dirty=False,
        router_model="gemini-3.5-flash-lite",
        chat_model="gemini-3.5-flash",
        embedding_model="gemini-embedding-2",
        top_k=4,
        rag_min_similarity=0.60,
        dataset_path="evaluation/dataset_verified.json",
        dataset_version="1.0",
        dataset_has_unreviewed=False,
        vector_index_fingerprint="f7eb5b68f15bfb63...",
    )
    assert meta.router_model == "gemini-3.5-flash-lite"
    assert meta.chat_model == "gemini-3.5-flash"
    assert meta.embedding_model == "gemini-embedding-2"


def test_reporter_displays_three_models_separately():
    """Verify generate_markdown_summary outputs Source Router Model, RAG Generation Model, and Embedding Model."""
    meta = EvaluationRunMetadata(
        timestamp="2026-09-01T12:00:00Z",
        git_commit="abcdef0",
        git_dirty=False,
        router_model="gemini-3.5-flash-lite",
        chat_model="gemini-3.5-flash",
        embedding_model="gemini-embedding-2",
        top_k=4,
        rag_min_similarity=0.60,
        dataset_path="evaluation/dataset_verified.json",
        dataset_version="1.0",
        dataset_has_unreviewed=False,
        vector_index_fingerprint="f7eb5b68f15bfb63...",
    )
    report = EvaluationReport(
        metadata=meta,
        router_summary=RouterSummaryMetrics(
            total_evaluable_cases=15,
            correct_routes=15,
            router_accuracy=1.0,
            confusion_matrix={"internal": {"internal": 5, "external": 0, "all": 0}},
        ),
        retrieval_summary=RetrievalSummaryMetrics(
            total_answerable_cases=15,
            hit_at_k_rate=1.0,
            mean_reciprocal_rank=1.0,
            mean_expected_source_recall_at_k=1.0,
            scope_compliance_rate=1.0,
            dual_source_coverage_rate=1.0,
        ),
        abstention_summary=AbstentionSummaryMetrics(
            total_cases=20,
            tp_abstain=5,
            fp_abstain=0,
            tn_abstain=15,
            fn_abstain=0,
            abstention_accuracy=1.0,
            abstention_precision=1.0,
            abstention_recall=1.0,
        ),
        generation_summary=CitationAndGenerationSummaryMetrics(
            total_answerable_cases=15,
            total_generated_answers=15,
            citation_integrity_rate=1.0,
            traceable_answer_success_rate=1.0,
        ),
        cases=[],
    )

    summary_md = generate_markdown_summary(report)
    assert "**Source Router Model**: `gemini-3.5-flash-lite`" in summary_md
    assert "**RAG Generation Model**: `gemini-3.5-flash`" in summary_md
    assert "**Embedding Model**: `gemini-embedding-2`" in summary_md
