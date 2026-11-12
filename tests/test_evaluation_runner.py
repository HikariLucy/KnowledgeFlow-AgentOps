"""Offline unit tests for evaluation runner orchestration."""

from pathlib import Path
from langchain_core.documents import Document
import pytest

from app.agents.source_router import FakeSourceRouter
from app.core.config import Settings
from app.evaluation.dataset import save_dataset
from app.evaluation.runner import run_evaluation
from app.evaluation.schemas import EvaluationCase, EvaluationDataset
from app.rag.embeddings import DeterministicFakeEmbeddings
from app.rag.generator import FakeRAGGenerator
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import Retriever
from app.rag.vectorstore import VectorStore


@pytest.fixture
def fake_eval_pipeline():
    """Create a deterministic offline RAGPipeline fixture for runner testing."""
    docs = [
        Document(
            page_content="Procedimiento de incidentes de seguridad.",
            metadata={"source": "internal/procedimiento_incidentes.md", "source_type": "internal", "file_name": "procedimiento_incidentes.md", "chunk_index": 0},
        ),
        Document(
            page_content="Estándares de seguridad de datos.",
            metadata={"source": "external/referencia_seguridad.txt", "source_type": "external", "file_name": "referencia_seguridad.txt", "chunk_index": 0},
        ),
    ]
    settings = Settings(embedding_dimension=768, retrieval_top_k=2, rag_min_similarity=0.0)
    provider = DeterministicFakeEmbeddings(768)
    embeddings = provider.embed_documents(docs)
    vectorstore = VectorStore.from_documents(docs, embeddings, settings=settings)
    retriever = Retriever(vectorstore=vectorstore, embeddings=provider, settings=settings)
    router = FakeSourceRouter()
    generator = FakeRAGGenerator()

    return RAGPipeline(
        retriever=retriever,
        router=router,
        generator=generator,
        settings=settings,
    )


def test_runner_offline_execution_and_reporting(tmp_path, fake_eval_pipeline):
    """Verify evaluation runner executes completely offline and saves JSON and Markdown artifacts."""
    cases = [
        EvaluationCase(
            id="RUNNER-01",
            query="¿Cómo reportar un incidente?",
            category="internal",
            expected_scope="internal",
            answerable=True,
            expected_source_types=["internal"],
            expected_files=["procedimiento_incidentes.md"],
            expected_behavior="grounded_answer",
            human_reviewed=False,
        ),
        EvaluationCase(
            id="RUNNER-02",
            query="¿Pregunta de física?",
            category="out_of_domain",
            expected_scope=None,
            answerable=False,
            expected_source_types=[],
            expected_files=[],
            expected_behavior="abstain",
            human_reviewed=False,
        ),
    ]
    dataset = EvaluationDataset(
        version="1.0",
        description="Dataset para runner offline",
        cases=cases,
    )
    dataset_file = tmp_path / "test_dataset.json"
    save_dataset(dataset, dataset_file)

    output_dir = tmp_path / "results"

    report = run_evaluation(
        dataset_path=str(dataset_file),
        output_dir=str(output_dir),
        require_reviewed=False,
        require_clean=False,
        delay_seconds=0.0,
        top_k=2,
        pipeline=fake_eval_pipeline,
    )

    assert len(report.cases) == 2
    assert report.router_summary.total_evaluable_cases == 1
    assert report.retrieval_summary.total_answerable_cases == 1
    assert report.abstention_summary.total_cases == 2

    # Verify generated JSON and Markdown files
    json_files = list(output_dir.glob("*.json"))
    md_files = list(output_dir.glob("*.md"))

    assert len(json_files) == 1
    assert len(md_files) == 1

    md_content = md_files[0].read_text(encoding="utf-8")
    assert "# KnowledgeFlow RAG — Reporte de Evaluación Sistemática" in md_content
    assert "Router Accuracy" in md_content
    assert "Hit@2 Rate" in md_content


def test_runner_require_reviewed_gate(tmp_path, fake_eval_pipeline):
    """Verify runner aborts when require_reviewed is True and dataset has unreviewed cases."""
    case = EvaluationCase(
        id="RUNNER-GATE",
        query="Consulta",
        category="internal",
        expected_scope="internal",
        answerable=True,
        expected_source_types=["internal"],
        expected_files=["procedimiento_incidentes.md"],
        expected_behavior="grounded_answer",
        human_reviewed=False,
    )
    dataset = EvaluationDataset(
        description="Dataset unreviewed",
        cases=[case],
    )
    dataset_file = tmp_path / "unreviewed_dataset.json"
    save_dataset(dataset, dataset_file)

    with pytest.raises(ValueError, match="unreviewed cases"):
        run_evaluation(
            dataset_path=str(dataset_file),
            output_dir=str(tmp_path / "results"),
            require_reviewed=True,
            pipeline=fake_eval_pipeline,
        )


def test_router_error_does_not_contaminate_isolated_retrieval(tmp_path, fake_eval_pipeline):
    """Verify that a routing error does NOT penalize isolated retrieval gold metrics."""
    # Force router to wrongly return 'external' for an internal question
    fake_eval_pipeline.router.default_scope = "external"

    case = EvaluationCase(
        id="ISO-01",
        query="¿Cómo reportar un incidente?",
        category="internal",
        expected_scope="internal",
        answerable=True,
        expected_source_types=["internal"],
        expected_files=["procedimiento_incidentes.md"],
        expected_behavior="grounded_answer",
        human_reviewed=False,
    )
    dataset = EvaluationDataset(description="Test isolation", cases=[case])
    dataset_file = tmp_path / "iso_dataset.json"
    save_dataset(dataset, dataset_file)

    report = run_evaluation(
        dataset_path=str(dataset_file),
        output_dir=str(tmp_path / "results"),
        require_reviewed=False,
        top_k=2,
        pipeline=fake_eval_pipeline,
    )

    # Router was wrong: expected internal, predicted external
    assert report.router_summary.router_accuracy == 0.0
    assert report.cases[0].router_result.is_correct is False

    # Isolated retrieval evaluated with expected_scope='internal' -> successfully found internal file!
    assert report.retrieval_summary.hit_at_k_rate == 1.0
    assert report.cases[0].retrieval_result.hit_at_k == 1.0
    assert report.cases[0].retrieval_result.source_scope_compliant is True


def test_retrieve_balanced_raw_preserves_quotas_pre_threshold():
    """Verify retrieve_balanced_raw preserves dual quotas without applying min_similarity cutoff."""
    docs = [
        Document(page_content="I1", metadata={"file_name": "i1.md", "source_type": "internal"}),
        Document(page_content="I2", metadata={"file_name": "i2.md", "source_type": "internal"}),
        Document(page_content="E1", metadata={"file_name": "e1.md", "source_type": "external"}),
        Document(page_content="E2", metadata={"file_name": "e2.md", "source_type": "external"}),
    ]
    # Set high rag_min_similarity that would normally filter everything in core pipeline
    settings = Settings(embedding_dimension=768, retrieval_top_k=4, rag_min_similarity=0.99)
    provider = DeterministicFakeEmbeddings(768)
    embeddings = provider.embed_documents(docs)
    vectorstore = VectorStore.from_documents(docs, embeddings, settings=settings)
    retriever = Retriever(vectorstore=vectorstore, embeddings=provider, settings=settings)

    from app.evaluation.retrieval_utils import retrieve_balanced_raw
    results = retrieve_balanced_raw(retriever, "query", top_k=4)

    # Must return 4 results (2 internal + 2 external) despite high min_similarity setting
    assert len(results) == 4
    types = [r.document.metadata.get("source_type") for r in results]
    assert types.count("internal") == 2
    assert types.count("external") == 2
