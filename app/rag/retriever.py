"""Semantic retrieval pipeline combining query embedding and FAISS vector search."""

from typing import List, Optional
from app.core.config import Settings, get_settings
from app.rag.embeddings import BaseEmbeddings, GeminiEmbeddings
from app.rag.schemas import SearchResult, SourceType
from app.rag.vectorstore import VectorStore


class Retriever:
    """Semantic retriever connecting query embedding to FAISS vector store search."""

    def __init__(
        self,
        vectorstore: VectorStore,
        embeddings: Optional[BaseEmbeddings] = None,
        settings: Optional[Settings] = None,
    ):
        self.vectorstore = vectorstore
        self.settings = settings or get_settings()
        self.embeddings = embeddings or GeminiEmbeddings(settings=self.settings)

    def search(
        self,
        query: str,
        k: Optional[int] = None,
        source_type: Optional[SourceType] = None,
    ) -> List[SearchResult]:
        """Execute semantic search for a query with optional source filtering.

        Args:
            query: User search query text.
            k: Top-K results to retrieve (defaults to settings.retrieval_top_k).
            source_type: Optional filter for 'internal' or 'external' documents.

        Returns:
            List of SearchResult objects sorted by descending cosine similarity.
        """
        if not query or not str(query).strip():
            raise ValueError("Query string cannot be empty or whitespace only.")

        top_k = k if k is not None else self.settings.retrieval_top_k
        if top_k <= 0:
            raise ValueError(f"k must be positive, got {top_k}")

        if source_type is not None and source_type not in ("internal", "external"):
            raise ValueError(
                f"Invalid source_type '{source_type}'. Expected 'internal', 'external', or None."
            )

        # Generate query embedding
        query_vector = self.embeddings.embed_query(query)

        # Perform similarity search in vectorstore
        return self.vectorstore.similarity_search(
            query_vector=query_vector,
            k=top_k,
            source_type=source_type,
        )
