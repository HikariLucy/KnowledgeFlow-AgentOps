"""Offline unit tests for complete RAG Pipeline orchestration."""

from unittest.mock import MagicMock
import pytest
from langchain_core.documents import Document

from app.agents.source_router import FakeSourceRouter
from app.core.config import Settings
from app.rag.embeddings import DeterministicFakeEmbeddings
from app.rag.generator import FakeRAGGenerator
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import Retriever
from app.rag.vectorstore import VectorStore


@pytest.fixture
def sample_vectorstore():
    """Builds an in-memory VectorStore with 3 internal and 3 external chunks."""
    docs = [
        # Internal docs
        Document(
            page_content="Política interna de contraseñas de NovaTech: 12 caracteres mínimo y rotación cada 90 días.",
            metadata={"source": "internal/passwords.md", "source_type": "internal", "file_name": "passwords.md", "chunk_index": 0},
        ),
        Document(
            page_content="Procedimiento interno de reporte de incidentes a soc@novatech-demo.local.",
            metadata={"source": "internal/incidentes.md", "source_type": "internal", "file_name": "incidentes.md", "chunk_index": 0},
        ),
        Document(
            page_content="Gestión de accesos y permisos por roles RBAC en sistemas internos.",
            metadata={"source": "internal/accesos.md", "source_type": "internal", "file_name": "accesos.md", "chunk_index": 0},
        ),
        # External docs
        Document(
            page_content="OWASP Top 10: Prevención de inyecciones SQL y fallos de autenticación.",
            metadata={"source": "external/owasp.md", "source_type": "external", "file_name": "owasp.md", "chunk_index": 0},
        ),
        Document(
            page_content="Estándar NIST SP 800-63B sobre guías de identidad y contraseñas digitales.",
            metadata={"source": "external/nist.txt", "source_type": "external", "file_name": "nist.txt", "chunk_index": 0},
        ),
        Document(
            page_content="Norma ISO 27001 sobre controles de seguridad de la información.",
            metadata={"source": "external/iso.txt", "source_type": "external", "file_name": "iso.txt", "chunk_index": 0},
        ),
    ]

    settings = Settings(embedding_dimension=768, retrieval_top_k=4, rag_min_similarity=0.0)
    provider = DeterministicFakeEmbeddings(768)
    embeddings = provider.embed_documents(docs)
    return VectorStore.from_documents(docs, embeddings, settings=settings)


def test_pipeline_internal_routing_filters_internal_only(sample_vectorstore):
    """Verify internal query routes to internal and retrieves exclusively internal sources."""
    settings = Settings(retrieval_top_k=4, rag_min_similarity=0.0)
    provider = DeterministicFakeEmbeddings(768)
    retriever = Retriever(vectorstore=sample_vectorstore, embeddings=provider, settings=settings)
    router = FakeSourceRouter(default_scope="internal")
    generator = FakeRAGGenerator()

    pipeline = RAGPipeline(retriever=retriever, router=router, generator=generator, settings=settings)
    answer = pipeline.run("¿Cómo son las contraseñas internas?")

    assert answer.source_scope == "internal"
    assert answer.abstained is False
    assert len(answer.sources) > 0
    for s in answer.sources:
        assert s.source_type == "internal"


def test_pipeline_external_routing_filters_external_only(sample_vectorstore):
    """Verify external query routes to external and retrieves exclusively external sources."""
    settings = Settings(retrieval_top_k=4, rag_min_similarity=0.0)
    provider = DeterministicFakeEmbeddings(768)
    retriever = Retriever(vectorstore=sample_vectorstore, embeddings=provider, settings=settings)
    router = FakeSourceRouter(default_scope="external")
    generator = FakeRAGGenerator()

    pipeline = RAGPipeline(retriever=retriever, router=router, generator=generator, settings=settings)
    answer = pipeline.run("¿Qué dice el estándar OWASP?")

    assert answer.source_scope == "external"
    assert answer.abstained is False
    assert len(answer.sources) > 0
    for s in answer.sources:
        assert s.source_type == "external"


def test_pipeline_all_scope_balanced_retrieval(sample_vectorstore):
    """Verify source_scope='all' performs balanced dual retrieval combining internal and external."""
    settings = Settings(retrieval_top_k=4, rag_min_similarity=0.0)
    provider = DeterministicFakeEmbeddings(768)
    retriever = Retriever(vectorstore=sample_vectorstore, embeddings=provider, settings=settings)
    router = FakeSourceRouter(default_scope="all")
    generator = FakeRAGGenerator()

    pipeline = RAGPipeline(retriever=retriever, router=router, generator=generator, settings=settings)
    answer = pipeline.run("Compara políticas internas de contraseñas con el estándar NIST")

    assert answer.source_scope == "all"
    assert len(answer.sources) <= 4

    types = {s.source_type for s in answer.sources}
    # Balanced all should have both internal and external if available
    assert "internal" in types
    assert "external" in types


def test_pipeline_top_k_limit(sample_vectorstore):
    """Verify pipeline respects top_k limit."""
    settings = Settings(retrieval_top_k=2, rag_min_similarity=0.0)
    provider = DeterministicFakeEmbeddings(768)
    retriever = Retriever(vectorstore=sample_vectorstore, embeddings=provider, settings=settings)
    router = FakeSourceRouter(default_scope="all")
    generator = FakeRAGGenerator()

    pipeline = RAGPipeline(retriever=retriever, router=router, generator=generator, settings=settings)
    answer = pipeline.run("Consulta general", top_k=2)

    assert len(answer.sources) <= 2


def test_pipeline_early_abstention_on_weak_evidence(sample_vectorstore):
    """Verify early abstention when no chunks meet the similarity threshold, without calling generator."""
    # Set high similarity threshold so nothing matches
    settings = Settings(retrieval_top_k=4, rag_min_similarity=0.999)
    provider = DeterministicFakeEmbeddings(768)
    retriever = Retriever(vectorstore=sample_vectorstore, embeddings=provider, settings=settings)
    router = FakeSourceRouter(default_scope="internal")

    mock_generator = MagicMock(spec=FakeRAGGenerator)

    pipeline = RAGPipeline(retriever=retriever, router=router, generator=mock_generator, settings=settings)
    answer = pipeline.run("Consulta fuera de dominio")

    assert answer.abstained is True
    assert "No encontré evidencia suficiente" in answer.answer
    assert answer.citations == []
    assert answer.sources == []
    # Assert generator was NOT called
    mock_generator.generate.assert_not_called()


def test_pipeline_manual_source_scope_override(sample_vectorstore):
    """Verify passing explicit source_scope bypasses router classification."""
    settings = Settings(retrieval_top_k=4, rag_min_similarity=0.0)
    provider = DeterministicFakeEmbeddings(768)
    retriever = Retriever(vectorstore=sample_vectorstore, embeddings=provider, settings=settings)

    mock_router = MagicMock(spec=FakeSourceRouter)
    generator = FakeRAGGenerator()

    pipeline = RAGPipeline(retriever=retriever, router=mock_router, generator=generator, settings=settings)
    answer = pipeline.run("Consulta con override", source_scope="external")

    assert answer.source_scope == "external"
    mock_router.route.assert_not_called()
    for s in answer.sources:
        assert s.source_type == "external"
