"""Tests for semantic long-term memory retrieval."""

from langchain_core.documents import Document

from app.memory.long_term import LongTermMemoryStore
from app.memory.models import MemoryCreate
from app.memory.semantic import SemanticMemory
from app.rag.embeddings import BaseEmbeddings
from app.storage.database import SQLiteDatabase


class KeywordEmbeddings(BaseEmbeddings):
    """Tiny deterministic embedding provider for memory tests."""

    @staticmethod
    def _vector(text: str) -> list[float]:
        text = text.lower()

        if "mfa" in text or "autenticador" in text:
            return [1.0, 0.0, 0.0]

        if "vpn" in text:
            return [0.0, 1.0, 0.0]

        return [0.0, 0.0, 1.0]

    def embed_document(
        self,
        document,
        metadata=None,
    ) -> list[float]:
        if isinstance(document, Document):
            text = document.page_content
        else:
            text = str(document)

        return self._vector(text)

    def embed_documents(self, documents):
        return [
            self.embed_document(document)
            for document in documents
        ]

    def embed_query(self, query: str) -> list[float]:
        return self._vector(query)


def _semantic_memory(tmp_path):
    database = SQLiteDatabase(tmp_path / "semantic-memory.db")
    database.initialize()

    store = LongTermMemoryStore(database)

    return SemanticMemory(
        store=store,
        embeddings=KeywordEmbeddings(),
    )


def test_semantic_memory_persists_embedding(tmp_path):
    memory = _semantic_memory(tmp_path)

    record = memory.remember(
        MemoryCreate(
            conversation_id="conv-1",
            content="El usuario perdió su autenticador MFA.",
            memory_type="event",
        )
    )

    assert record.embedding == [1.0, 0.0, 0.0]


def test_semantic_memory_ranks_relevant_memory_first(tmp_path):
    memory = _semantic_memory(tmp_path)

    memory.remember(
        MemoryCreate(
            conversation_id="conv-1",
            content="El usuario perdió su autenticador MFA.",
        )
    )

    memory.remember(
        MemoryCreate(
            conversation_id="conv-1",
            content="El usuario reportó un problema de VPN.",
        )
    )

    results = memory.search(
        query="¿Qué ocurrió con el MFA?",
        conversation_id="conv-1",
        top_k=2,
    )

    assert len(results) == 2
    assert "MFA" in results[0].memory.content
    assert results[0].score > results[1].score


def test_semantic_memory_respects_conversation_filter(tmp_path):
    memory = _semantic_memory(tmp_path)

    memory.remember(
        MemoryCreate(
            conversation_id="conv-a",
            content="Problema con MFA.",
        )
    )

    memory.remember(
        MemoryCreate(
            conversation_id="conv-b",
            content="Otro problema con MFA.",
        )
    )

    results = memory.search(
        query="MFA",
        conversation_id="conv-a",
    )

    assert len(results) == 1
    assert results[0].memory.conversation_id == "conv-a"
