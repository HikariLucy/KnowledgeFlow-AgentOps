"""Offline unit tests for semantic Retriever pipeline."""

import pytest
from langchain_core.documents import Document

from app.core.config import Settings
from app.rag.embeddings import DeterministicFakeEmbeddings
from app.rag.retriever import Retriever
from app.rag.vectorstore import VectorStore


@pytest.fixture
def retriever_fixture():
    """Builds an in-memory retriever with 4 test documents."""
    docs = [
        Document(
            page_content="Las contraseñas deben tener al menos 12 caracteres y rotar cada 90 días.",
            metadata={
                "source": "knowledge/internal/passwords.md",
                "source_type": "internal",
                "file_name": "passwords.md",
                "chunk_index": 0,
            },
        ),
        Document(
            page_content="Reporte de incidentes de seguridad al correo soc@empresa.com inmediatamente.",
            metadata={
                "source": "knowledge/internal/incidentes.md",
                "source_type": "internal",
                "file_name": "incidentes.md",
                "chunk_index": 0,
            },
        ),
        Document(
            page_content="OWASP Guía de prevención de inyección SQL y XSS en APIs REST.",
            metadata={
                "source": "knowledge/external/owasp_top10.md",
                "source_type": "external",
                "file_name": "owasp_top10.md",
                "chunk_index": 0,
            },
        ),
        Document(
            page_content="Estándares ISO 27001 para la implementación de un SGSI empresarial.",
            metadata={
                "source": "knowledge/external/iso27001.txt",
                "source_type": "external",
                "file_name": "iso27001.txt",
                "chunk_index": 0,
            },
        ),
    ]

    settings = Settings(
        embedding_dimension=768,
        retrieval_top_k=3,
    )
    provider = DeterministicFakeEmbeddings(embedding_dimension=768)
    embeddings = provider.embed_documents(docs)
    vs = VectorStore.from_documents(docs, embeddings, settings=settings)
    retriever = Retriever(vectorstore=vs, embeddings=provider, settings=settings)
    return retriever


def test_retriever_search_returns_ranked_results(retriever_fixture):
    """Verify retriever search returns ranked SearchResult objects with scores."""
    results = retriever_fixture.search("¿Cómo reportar incidentes?", k=2)

    assert len(results) == 2
    assert results[0].rank == 1
    assert results[1].rank == 2
    assert results[0].score >= results[1].score
    assert isinstance(results[0].document, Document)


def test_retriever_search_respects_top_k(retriever_fixture):
    """Verify retriever returns at most K results."""
    results_k1 = retriever_fixture.search("seguridad", k=1)
    assert len(results_k1) == 1

    results_k4 = retriever_fixture.search("seguridad", k=4)
    assert len(results_k4) == 4


def test_retriever_empty_query_raises(retriever_fixture):
    """Verify empty or whitespace query raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        retriever_fixture.search("")

    with pytest.raises(ValueError, match="cannot be empty"):
        retriever_fixture.search("    ")


def test_retriever_invalid_k_raises(retriever_fixture):
    """Verify k <= 0 raises ValueError."""
    with pytest.raises(ValueError, match="positive"):
        retriever_fixture.search("test", k=0)

    with pytest.raises(ValueError, match="positive"):
        retriever_fixture.search("test", k=-5)


def test_retriever_invalid_source_type_raises(retriever_fixture):
    """Verify invalid source_type raises ValueError."""
    with pytest.raises(ValueError, match="Invalid source_type"):
        retriever_fixture.search("test", source_type="secret")  # type: ignore


def test_retriever_filter_internal_only(retriever_fixture):
    """Verify retriever internal filter returns exclusively internal documents."""
    results = retriever_fixture.search("seguridad", k=4, source_type="internal")
    assert len(results) == 2
    for r in results:
        assert r.document.metadata["source_type"] == "internal"


def test_retriever_filter_external_only(retriever_fixture):
    """Verify retriever external filter returns exclusively external documents."""
    results = retriever_fixture.search("seguridad", k=4, source_type="external")
    assert len(results) == 2
    for r in results:
        assert r.document.metadata["source_type"] == "external"


def test_run_search_aborts_on_stale_index(tmp_path):
    """Verify run_search aborts with exit code 1 when vectorstore is stale."""
    from app.rag.search import run_search

    # Create dummy knowledge dir
    kb_dir = tmp_path / "kb"
    internal_dir = kb_dir / "internal"
    internal_dir.mkdir(parents=True)
    doc_file = internal_dir / "doc.txt"
    doc_file.write_text("Contenido inicial para indexar.", encoding="utf-8")

    # Create index in tmp dir
    from app.rag.loaders import load_knowledge_base
    from app.rag.chunking import split_documents

    settings = Settings()
    docs = load_knowledge_base(str(kb_dir))
    chunks = split_documents(docs, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    provider = DeterministicFakeEmbeddings(768)
    embeddings = provider.embed_documents(chunks)
    vs = VectorStore.from_documents(chunks, embeddings, settings=settings)
    vs_dir = tmp_path / "vs"
    vs.save_local(vs_dir)

    # Modify knowledge dir file to make index stale
    doc_file.write_text("Texto completamente diferente posterior.", encoding="utf-8")

    # run_search should abort via sys.exit(1)
    with pytest.raises(SystemExit) as exc_info:
        run_search(
            query="test",
            k=2,
            vectorstore_dir=str(vs_dir),
            knowledge_dir=str(kb_dir),
            embeddings_provider=provider,
            settings=settings,
            enforce_freshness=True,
        )
    assert exc_info.value.code == 1
