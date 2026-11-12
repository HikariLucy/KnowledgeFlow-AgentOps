"""Embedding services and input preparation for Gemini and FAISS retrieval."""

import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Union
from langchain_core.documents import Document
import numpy as np

from app.core.config import Settings, get_settings
from app.llm.client import GeminiClient, get_gemini_client


def get_document_title(metadata: Optional[Dict[str, Any]] = None) -> str:
    """Extract document title following strict priority hierarchy.

    Hierarchy:
        1. metadata["title"] if present and non-empty.
        2. metadata["file_name"] if present and non-empty.
        3. "none".

    Args:
        metadata: Optional document metadata dictionary.

    Returns:
        Extracted title string or "none".
    """
    if not metadata:
        return "none"

    title = metadata.get("title")
    if title is not None and str(title).strip():
        return str(title).strip()

    file_name = metadata.get("file_name")
    if file_name is not None and str(file_name).strip():
        return str(file_name).strip()

    return "none"


def prepare_document_for_embedding(
    content: str, metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Format document chunk content for Gemini Embedding 2 retrieval.

    Format:
        title: {title} | text: {content}

    Args:
        content: Raw chunk text content.
        metadata: Optional metadata dictionary containing title/file_name.

    Returns:
        Formatted string for embedding generation.
    """
    if not content or not content.strip():
        raise ValueError("Document content cannot be empty or whitespace only.")

    title = get_document_title(metadata)
    return f"title: {title} | text: {content.strip()}"


def prepare_query_for_embedding(query: str) -> str:
    """Format search query for asymmetric retrieval with Gemini Embedding 2.

    Format:
        task: search result | query: {query}

    Args:
        query: Raw user query string.

    Returns:
        Formatted string for embedding generation.
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty or whitespace only.")

    return f"task: search result | query: {query.strip()}"


class BaseEmbeddings(ABC):
    """Abstract base class / interface for embedding providers."""

    @abstractmethod
    def embed_document(
        self,
        document: Union[Document, str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[float]:
        """Generate embedding vector for a single document or text."""
        pass

    @abstractmethod
    def embed_documents(
        self, documents: Sequence[Union[Document, str]]
    ) -> List[List[float]]:
        """Generate embedding vectors for a sequence of documents."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding vector for a search query."""
        pass


class GeminiEmbeddings(BaseEmbeddings):
    """Google Gemini Embedding 2 implementation using decoupled GeminiClient."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        gemini_client: Optional[GeminiClient] = None,
    ):
        self.settings = settings or get_settings()
        self.gemini_client = gemini_client or get_gemini_client(self.settings)
        self.embedding_model = self.settings.gemini_embedding_model
        self.embedding_dimension = self.settings.embedding_dimension

    def _call_embed_api(self, formatted_text: str) -> List[float]:
        """Execute embed_content call via Google GenAI SDK.

        Args:
            formatted_text: Asymmetric retrieval prepared text.

        Returns:
            List of float embedding values.
        """
        client = self.gemini_client.get_client()

        try:
            response = client.models.embed_content(
                model=self.embedding_model,
                contents=formatted_text,
                config={"output_dimensionality": self.embedding_dimension},
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to generate embedding from Gemini API ({self.embedding_model}): {e}"
            ) from e

        if not response or not response.embeddings:
            raise RuntimeError("Gemini API returned an empty embedding response.")

        vector = response.embeddings[0].values
        if len(vector) != self.embedding_dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.embedding_dimension}, got {len(vector)}"
            )

        return list(vector)

    def embed_document(
        self,
        document: Union[Document, str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[float]:
        """Generate embedding for a single document."""
        if isinstance(document, Document):
            content = document.page_content
            meta = document.metadata
        else:
            content = document
            meta = metadata or {}

        formatted_text = prepare_document_for_embedding(content, meta)
        return self._call_embed_api(formatted_text)

    def embed_documents(
        self, documents: Sequence[Union[Document, str]]
    ) -> List[List[float]]:
        """Generate embeddings ensuring exact 1 chunk -> 1 vector cardinality."""
        if not documents:
            return []

        embeddings: List[List[float]] = []
        for doc in documents:
            vector = self.embed_document(doc)
            embeddings.append(vector)

        if len(embeddings) != len(documents):
            raise RuntimeError(
                f"Cardinality contract violation: expected {len(documents)} vectors, got {len(embeddings)}"
            )

        return embeddings

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a search query."""
        formatted_query = prepare_query_for_embedding(query)
        return self._call_embed_api(formatted_query)


class DeterministicFakeEmbeddings(BaseEmbeddings):
    """Deterministic, offline fake embeddings provider for testing and validation."""

    def __init__(self, embedding_dimension: int = 768):
        if embedding_dimension <= 0:
            raise ValueError(
                f"embedding_dimension must be positive, got {embedding_dimension}"
            )
        self.embedding_dimension = embedding_dimension

    def _generate_vector(self, text: str) -> List[float]:
        """Generate a deterministic, unit-normalized vector from text hash."""
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text.")

        # Derive 32-bit integer seed from sha256 of text
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:4], byteorder="big", signed=False)
        rng = np.random.RandomState(seed)

        # Generate Gaussian vector and normalize to unit L2 norm
        vec = rng.randn(self.embedding_dimension).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.tolist()

    def embed_document(
        self,
        document: Union[Document, str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[float]:
        """Generate deterministic fake embedding for a document."""
        if isinstance(document, Document):
            content = document.page_content
            meta = document.metadata
        else:
            content = document
            meta = metadata or {}

        formatted_text = prepare_document_for_embedding(content, meta)
        return self._generate_vector(formatted_text)

    def embed_documents(
        self, documents: Sequence[Union[Document, str]]
    ) -> List[List[float]]:
        """Generate deterministic embeddings verifying cardinality."""
        if not documents:
            return []

        embeddings: List[List[float]] = []
        for doc in documents:
            vector = self.embed_document(doc)
            embeddings.append(vector)

        if len(embeddings) != len(documents):
            raise RuntimeError(
                f"Cardinality contract violation: expected {len(documents)} vectors, got {len(embeddings)}"
            )

        return embeddings

    def embed_query(self, query: str) -> List[float]:
        """Generate deterministic fake embedding for a query."""
        formatted_query = prepare_query_for_embedding(query)
        return self._generate_vector(formatted_query)
