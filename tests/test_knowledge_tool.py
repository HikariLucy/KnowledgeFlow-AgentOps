"""Tests for the agent-facing Knowledge RAG tool."""

import pytest
from langchain_core.documents import Document
from pydantic import ValidationError

from app.agents.source_router import FakeSourceRouter
from app.core.config import Settings
from app.rag.embeddings import DeterministicFakeEmbeddings
from app.rag.generator import FakeRAGGenerator
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import Retriever
from app.rag.schemas import RAGAnswer, SourceReference
from app.rag.vectorstore import VectorStore
from app.tools.knowledge import KnowledgeRAGTool
from app.tools.schemas import KnowledgeQueryInput


class StubRAGPipeline:
    """Minimal deterministic pipeline double for adapter-level tests."""

    def __init__(self, answer: RAGAnswer) -> None:
        self.answer = answer
        self.calls: list[dict] = []

    def run(
        self,
        query: str,
        source_scope=None,
        top_k=None,
    ) -> RAGAnswer:
        self.calls.append(
            {
                "query": query,
                "source_scope": source_scope,
                "top_k": top_k,
            }
        )
        return self.answer


def test_knowledge_tool_forwards_arguments_and_returns_structured_result():
    pipeline = StubRAGPipeline(
        RAGAnswer(
            query="¿Qué exige la política de accesos?",
            source_scope="internal",
            answer="La política exige control de accesos [S1].",
            citations=["S1"],
            sources=[
                SourceReference(
                    id="S1",
                    file_name="accesos.md",
                    source_type="internal",
                    chunk_index=0,
                    score=0.91,
                )
            ],
            abstained=False,
        )
    )

    tool = KnowledgeRAGTool(pipeline=pipeline)

    result = tool.run(
        KnowledgeQueryInput(
            query=" ¿Qué exige la política de accesos? ",
            source_scope="internal",
            top_k=3,
        )
    )

    assert pipeline.calls == [
        {
            "query": "¿Qué exige la política de accesos?",
            "source_scope": "internal",
            "top_k": 3,
        }
    ]

    assert result.abstained is False
    assert result.citations == ["S1"]
    assert len(result.sources) == 1
    assert result.sources[0].file_name == "accesos.md"
    assert result.sources[0].score == 0.91


def test_knowledge_tool_preserves_controlled_abstention():
    pipeline = StubRAGPipeline(
        RAGAnswer(
            query="Consulta sin evidencia",
            source_scope="all",
            answer=(
                "No encontré evidencia suficiente en las fuentes disponibles "
                "para responder esta consulta."
            ),
            citations=[],
            sources=[],
            abstained=True,
        )
    )

    tool = KnowledgeRAGTool(pipeline=pipeline)

    result = tool.run(
        KnowledgeQueryInput(
            query="Consulta sin evidencia",
        )
    )

    assert result.abstained is True
    assert result.citations == []
    assert result.sources == []


def test_knowledge_query_input_rejects_blank_query():
    with pytest.raises(ValidationError):
        KnowledgeQueryInput(query="   ")


def test_knowledge_query_input_validates_top_k():
    valid = KnowledgeQueryInput(
        query="Consulta válida",
        top_k=5,
    )

    assert valid.top_k == 5

    with pytest.raises(ValidationError):
        KnowledgeQueryInput(
            query="Consulta válida",
            top_k=0,
        )

    with pytest.raises(ValidationError):
        KnowledgeQueryInput(
            query="Consulta válida",
            top_k=21,
        )


def test_knowledge_tool_integrates_with_offline_rag_pipeline():
    docs = [
        Document(
            page_content=(
                "NovaTech utiliza controles de acceso basados en roles "
                "para proteger sus sistemas internos."
            ),
            metadata={
                "source": "internal/accesos.md",
                "source_type": "internal",
                "file_name": "accesos.md",
                "chunk_index": 0,
            },
        )
    ]

    settings = Settings(
        retrieval_top_k=1,
        rag_min_similarity=0.0,
    )

    embeddings = DeterministicFakeEmbeddings(
        settings.embedding_dimension
    )

    vectors = embeddings.embed_documents(docs)

    vectorstore = VectorStore.from_documents(
        docs,
        vectors,
        settings=settings,
    )

    retriever = Retriever(
        vectorstore=vectorstore,
        embeddings=embeddings,
        settings=settings,
    )

    pipeline = RAGPipeline(
        retriever=retriever,
        router=FakeSourceRouter(default_scope="internal"),
        generator=FakeRAGGenerator(),
        settings=settings,
    )

    tool = KnowledgeRAGTool(pipeline=pipeline)

    result = tool.run(
        KnowledgeQueryInput(
            query="¿Cómo protege NovaTech sus accesos?",
            source_scope="internal",
        )
    )

    assert result.abstained is False
    assert result.source_scope == "internal"
    assert result.citations == ["S1"]
    assert len(result.sources) == 1
    assert result.sources[0].source_type == "internal"
    assert result.sources[0].file_name == "accesos.md"
