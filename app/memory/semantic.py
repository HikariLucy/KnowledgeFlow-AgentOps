"""Semantic retrieval over persistent long-term memories."""

import numpy as np

from app.memory.long_term import LongTermMemoryStore
from app.memory.models import (
    MemoryCreate,
    MemoryRecord,
    SemanticMemoryResult,
)
from app.rag.embeddings import BaseEmbeddings


class SemanticMemory:
    """Persist memories with embeddings and retrieve relevant past context."""

    def __init__(
        self,
        store: LongTermMemoryStore,
        embeddings: BaseEmbeddings,
    ) -> None:
        self.store = store
        self.embeddings = embeddings

    def remember(self, data: MemoryCreate) -> MemoryRecord:
        """Embed and persist one long-term memory."""
        vector = self.embeddings.embed_document(
            data.content,
            metadata={
                "title": f"{data.memory_type.value} memory",
            },
        )

        return self.store.add_memory(
            data=data,
            embedding=vector,
        )

    def search(
        self,
        query: str,
        conversation_id: str | None = None,
        top_k: int = 4,
        min_similarity: float = 0.0,
    ) -> list[SemanticMemoryResult]:
        """Retrieve the most semantically similar persisted memories."""
        query = query.strip()

        if not query:
            raise ValueError("query cannot be empty")

        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        if not (-1.0 <= min_similarity <= 1.0):
            raise ValueError(
                "min_similarity must be between -1.0 and 1.0"
            )

        memories = self.store.list_memories(
            conversation_id=conversation_id
        )

        query_vector = np.asarray(
            self.embeddings.embed_query(query),
            dtype=np.float32,
        )

        query_norm = np.linalg.norm(query_vector)
        if query_norm == 0:
            raise ValueError("query embedding cannot have zero norm")

        results: list[SemanticMemoryResult] = []

        for memory in memories:
            if not memory.embedding:
                continue

            memory_vector = np.asarray(
                memory.embedding,
                dtype=np.float32,
            )

            memory_norm = np.linalg.norm(memory_vector)
            if memory_norm == 0:
                continue

            score = float(
                np.dot(query_vector, memory_vector)
                / (query_norm * memory_norm)
            )

            if score >= min_similarity:
                results.append(
                    SemanticMemoryResult(
                        memory=memory,
                        score=score,
                    )
                )

        results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        return results[:top_k]
