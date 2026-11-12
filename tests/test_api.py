"""Offline unit tests for FastAPI /api/query endpoint."""

from fastapi.testclient import TestClient
from langchain_core.documents import Document
import pytest

from app.agents.source_router import FakeSourceRouter
from app.api.routes import get_rag_pipeline
from app.core.config import Settings, get_settings
from app.main import app
from app.rag.embeddings import DeterministicFakeEmbeddings
from app.rag.generator import FakeRAGGenerator
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import Retriever
from app.rag.vectorstore import VectorStore


@pytest.fixture
def fake_rag_pipeline():
    """Builds a test RAGPipeline."""
    docs = [
        Document(
            page_content="Política interna de accesos y permisos RBAC.",
            metadata={"source": "internal/accesos.md", "source_type": "internal", "file_name": "accesos.md", "chunk_index": 0},
        )
    ]
    settings = Settings(retrieval_top_k=2, rag_min_similarity=0.0)
    provider = DeterministicFakeEmbeddings(768)
    embeddings = provider.embed_documents(docs)
    vs = VectorStore.from_documents(docs, embeddings, settings=settings)
    retriever = Retriever(vectorstore=vs, embeddings=provider, settings=settings)
    router = FakeSourceRouter(default_scope="internal")
    generator = FakeRAGGenerator()
    return RAGPipeline(retriever=retriever, router=router, generator=generator, settings=settings)


def test_api_health_endpoint():
    """Verify /health endpoint returns 200 OK."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_query_success(fake_rag_pipeline):
    """Verify POST /api/query returns 200 and satisfies schema."""
    import app.api.routes as api_routes
    api_routes._cached_pipeline = None

    app.dependency_overrides[get_rag_pipeline] = lambda: fake_rag_pipeline
    client = TestClient(app)

    response = client.post(
        "/api/query",
        json={"query": "¿Cómo se gestionan los accesos?"},
    )

    app.dependency_overrides.clear()
    api_routes._cached_pipeline = None

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "¿Cómo se gestionan los accesos?"
    assert data["source_scope"] == "internal"
    assert "answer" in data
    assert isinstance(data["citations"], list)
    assert isinstance(data["sources"], list)
    assert data["abstained"] is False


def test_api_query_empty_raises_422(fake_rag_pipeline):
    """Verify POST /api/query with empty query returns 422 Unprocessable Entity."""
    import app.api.routes as api_routes
    api_routes._cached_pipeline = None

    app.dependency_overrides[get_rag_pipeline] = lambda: fake_rag_pipeline
    client = TestClient(app)

    try:
        response = client.post(
            "/api/query",
            json={"query": "   "},
        )
    finally:
        app.dependency_overrides.clear()
        api_routes._cached_pipeline = None

    assert response.status_code == 422


def test_api_query_stale_or_missing_vectorstore_returns_503():
    """Verify POST /api/query returns 503 when vector store is missing or stale."""
    import app.api.routes as api_routes
    api_routes._cached_pipeline = None

    test_settings = Settings(vectorstore_dir="non_existent_vectorstore_dir")
    app.dependency_overrides[get_settings] = lambda: test_settings

    client = TestClient(app)
    response = client.post(
        "/api/query",
        json={"query": "Pregunta cuando no hay índice"},
    )

    app.dependency_overrides.clear()
    api_routes._cached_pipeline = None

    assert response.status_code == 503
    assert "python -m app.rag.indexer" in response.json()["detail"]
