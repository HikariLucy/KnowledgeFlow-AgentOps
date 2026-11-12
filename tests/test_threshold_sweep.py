"""Offline unit tests for similarity threshold sweep calibration tool."""

from langchain_core.documents import Document
import pytest

from app.agents.source_router import FakeSourceRouter
from app.core.config import Settings
from app.evaluation.dataset import save_dataset
from app.evaluation.schemas import EvaluationCase, EvaluationDataset
from app.evaluation.threshold_sweep import run_threshold_sweep
from app.rag.embeddings import DeterministicFakeEmbeddings
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import Retriever
from app.rag.vectorstore import VectorStore


@pytest.fixture
def fake_sweep_pipeline():
    """Create a deterministic offline RAGPipeline fixture for threshold sweep."""
    docs = [
        Document(
            page_content="Procedimiento de incidentes.",
            metadata={"source": "internal/procedimiento_incidentes.md", "source_type": "internal", "file_name": "procedimiento_incidentes.md", "chunk_index": 0},
        ),
    ]
    settings = Settings(embedding_dimension=768, retrieval_top_k=2, rag_min_similarity=0.60)
    provider = DeterministicFakeEmbeddings(768)
    embeddings = provider.embed_documents(docs)
    vectorstore = VectorStore.from_documents(docs, embeddings, settings=settings)
    retriever = Retriever(vectorstore=vectorstore, embeddings=provider, settings=settings)
    router = FakeSourceRouter()

    return RAGPipeline(
        retriever=retriever,
        router=router,
        settings=settings,
    )


def test_threshold_sweep_execution(tmp_path, fake_sweep_pipeline):
    """Verify threshold sweep computes local behavior without modifying Settings."""
    cases = [
        EvaluationCase(
            id="SWEEP-01",
            query="¿Cómo reportar incidentes?",
            category="internal",
            expected_scope="internal",
            answerable=True,
            expected_source_types=["internal"],
            expected_files=["procedimiento_incidentes.md"],
            expected_behavior="grounded_answer",
        ),
        EvaluationCase(
            id="SWEEP-02",
            query="¿Pregunta de cocina?",
            category="out_of_domain",
            expected_scope=None,
            answerable=False,
            expected_source_types=[],
            expected_files=[],
            expected_behavior="abstain",
        ),
    ]
    dataset = EvaluationDataset(
        description="Dataset para threshold sweep",
        cases=cases,
    )
    dataset_file = tmp_path / "sweep_dataset.json"
    save_dataset(dataset, dataset_file)

    test_thresholds = [0.50, 0.60, 0.70]
    results = run_threshold_sweep(
        dataset_path=str(dataset_file),
        thresholds=test_thresholds,
        top_k=2,
        pipeline=fake_sweep_pipeline,
    )

    assert "0.50" in results
    assert "0.60" in results
    assert "0.70" in results

    for key, data in results.items():
        assert "answerable_retained_rate" in data
        assert "false_abstention_rate" in data
        assert "correct_ood_abstention_rate" in data
        assert "ood_leakage_rate" in data
        assert "hit_at_k_rate" in data

    # Verify pipeline settings were not modified
    assert fake_sweep_pipeline.settings.rag_min_similarity == 0.60


def test_threshold_sweep_all_scope_preserves_balanced_quotas(tmp_path):
    """Verify threshold sweep on scope='all' preserves dual quotas even when internal scores dominate."""
    docs = [
        Document(page_content="I1", metadata={"file_name": "internal_1.md", "source_type": "internal"}),
        Document(page_content="I2", metadata={"file_name": "internal_2.md", "source_type": "internal"}),
        Document(page_content="I3", metadata={"file_name": "internal_3.md", "source_type": "internal"}),
        Document(page_content="I4", metadata={"file_name": "internal_4.md", "source_type": "internal"}),
        Document(page_content="E1", metadata={"file_name": "external_1.txt", "source_type": "external"}),
        Document(page_content="E2", metadata={"file_name": "external_2.txt", "source_type": "external"}),
    ]
    settings = Settings(embedding_dimension=768, retrieval_top_k=4, rag_min_similarity=0.60)
    provider = DeterministicFakeEmbeddings(768)
    embeddings = provider.embed_documents(docs)
    vectorstore = VectorStore.from_documents(docs, embeddings, settings=settings)
    retriever = Retriever(vectorstore=vectorstore, embeddings=provider, settings=settings)
    # Fake router routes to 'all'
    router = FakeSourceRouter(default_scope="all")
    pipeline = RAGPipeline(retriever=retriever, router=router, settings=settings)

    case = EvaluationCase(
        id="SWEEP-ALL",
        query="Compara interno y externo",
        category="all",
        expected_scope="all",
        answerable=True,
        expected_source_types=["internal", "external"],
        expected_files=["external_1.txt"],
        expected_behavior="grounded_answer",
    )
    dataset = EvaluationDataset(description="Test balanced sweep", cases=[case])
    dataset_file = tmp_path / "sweep_all.json"
    save_dataset(dataset, dataset_file)

    results = run_threshold_sweep(
        dataset_path=str(dataset_file),
        thresholds=[0.0],
        top_k=4,
        pipeline=pipeline,
    )

    # external_1.txt must be retained because of the 2 external quota
    assert results["0.00"]["hit_at_k_rate"] == 1.0
    assert results["0.00"]["answerable_retained_rate"] == 1.0
