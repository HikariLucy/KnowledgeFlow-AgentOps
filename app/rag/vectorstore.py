"""FAISS-based vector store with safe non-pickle persistence and semantic retrieval."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import faiss
from langchain_core.documents import Document
import numpy as np

from app.core.config import Settings, get_settings
from app.rag.schemas import IndexManifest, SearchResult, SerializedDocument, SourceType


def compute_index_fingerprint(
    documents: Sequence[Document],
    settings: Optional[Settings] = None,
) -> str:
    """Compute deterministic SHA-256 fingerprint for document corpus and configuration.

    The fingerprint deterministically hashes:
        - Each chunk's page_content and relevant metadata (source, source_type, file_name, chunk_index, page)
        - chunk_size
        - chunk_overlap
        - embedding_model
        - embedding_dimension

    Args:
        documents: Sequence of document chunks.
        settings: Application settings with chunking and embedding parameters.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    cfg = settings or get_settings()
    hasher = hashlib.sha256()

    # Hash configuration parameters
    config_repr = (
        f"model={cfg.gemini_embedding_model}|"
        f"dim={cfg.embedding_dimension}|"
        f"chunk_size={cfg.chunk_size}|"
        f"chunk_overlap={cfg.chunk_overlap}\n"
    )
    hasher.update(config_repr.encode("utf-8"))

    # Hash documents deterministically
    for doc in documents:
        meta = doc.metadata or {}
        doc_repr = (
            f"source={meta.get('source', '')}|"
            f"type={meta.get('source_type', '')}|"
            f"file={meta.get('file_name', '')}|"
            f"chunk={meta.get('chunk_index', '')}|"
            f"page={meta.get('page', '')}|"
            f"content={doc.page_content}\n"
        )
        hasher.update(doc_repr.encode("utf-8"))

    return hasher.hexdigest()


def validate_index_fingerprint(
    manifest: IndexManifest,
    current_documents: Sequence[Document],
    settings: Optional[Settings] = None,
) -> bool:
    """Validate if a persisted index manifest matches current corpus and settings.

    Args:
        manifest: Persisted IndexManifest loaded from disk.
        current_documents: Currently loaded and split document chunks.
        settings: Current application settings.

    Returns:
        True if fingerprints match exactly, False if index is stale or mismatched.
    """
    current_fingerprint = compute_index_fingerprint(current_documents, settings)
    return manifest.fingerprint == current_fingerprint


def verify_index_freshness(
    manifest: IndexManifest,
    knowledge_dir: str = "knowledge",
    settings: Optional[Settings] = None,
) -> bool:
    """Verify if persisted index manifest matches current knowledge corpus and settings.

    Args:
        manifest: Persisted IndexManifest loaded from disk.
        knowledge_dir: Path to directory with internal and external documents.
        settings: Application settings.

    Returns:
        True if index is fresh and valid, False if stale or mismatched.
    """
    from app.rag.chunking import split_documents
    from app.rag.loaders import load_knowledge_base

    cfg = settings or get_settings()
    current_docs = load_knowledge_base(knowledge_dir)
    current_chunks = split_documents(
        current_docs,
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
    )
    return validate_index_fingerprint(manifest, current_chunks, cfg)


class VectorStore:
    """FAISS vector store managing normalized vector indexing, retrieval and persistence."""

    INDEX_FILENAME = "index.faiss"
    DOCUMENTS_FILENAME = "documents.json"

    def __init__(
        self,
        index: faiss.Index,
        documents: List[Document],
        manifest: Optional[IndexManifest] = None,
        dimension: int = 768,
    ):
        self.index = index
        self.documents = documents
        self.manifest = manifest
        self.dimension = dimension

    @classmethod
    def from_documents(
        cls,
        documents: Sequence[Document],
        embeddings: Sequence[Sequence[float]],
        settings: Optional[Settings] = None,
    ) -> "VectorStore":
        """Build a FAISS vector store from document chunks and corresponding embedding vectors.

        Args:
            documents: Sequence of Document chunks.
            embeddings: Sequence of embedding vectors (one per chunk).
            settings: Optional application settings.

        Returns:
            Instantiated VectorStore.
        """
        cfg = settings or get_settings()
        dim = cfg.embedding_dimension

        if len(documents) != len(embeddings):
            raise ValueError(
                f"Documents and embeddings count mismatch: {len(documents)} docs vs {len(embeddings)} vectors"
            )

        # Create FAISS IndexFlatIP (Inner Product)
        faiss_index = faiss.IndexFlatIP(dim)

        if len(documents) > 0:
            np_vectors = np.array(embeddings, dtype=np.float32)
            if np_vectors.shape[1] != dim:
                raise ValueError(
                    f"Vector dimension mismatch: expected {dim}, got {np_vectors.shape[1]}"
                )
            # L2 normalize vectors so Inner Product equals Cosine Similarity
            faiss.normalize_L2(np_vectors)
            faiss_index.add(np_vectors)

        # Compute deterministic fingerprint and manifest
        fingerprint = compute_index_fingerprint(documents, cfg)
        serialized_docs = [
            SerializedDocument(page_content=doc.page_content, metadata=doc.metadata)
            for doc in documents
        ]

        manifest = IndexManifest(
            version="1.0",
            fingerprint=fingerprint,
            embedding_model=cfg.gemini_embedding_model,
            embedding_dimension=dim,
            chunk_size=cfg.chunk_size,
            chunk_overlap=cfg.chunk_overlap,
            total_documents=len(documents),
            created_at=datetime.now(timezone.utc).isoformat(),
            documents=serialized_docs,
        )

        return cls(
            index=faiss_index,
            documents=list(documents),
            manifest=manifest,
            dimension=dim,
        )

    def similarity_search(
        self,
        query_vector: Sequence[float],
        k: int = 4,
        source_type: Optional[SourceType] = None,
    ) -> List[SearchResult]:
        """Perform cosine similarity search with exact Top-K filtering.

        Args:
            query_vector: Embedding vector for the search query.
            k: Number of top results to return.
            source_type: Optional filter for 'internal' or 'external' sources.

        Returns:
            List of SearchResult objects ordered by cosine similarity descending.
        """
        if k <= 0:
            raise ValueError(f"k must be positive, got {k}")

        if source_type is not None and source_type not in ("internal", "external"):
            raise ValueError(
                f"Invalid source_type '{source_type}'. Expected 'internal', 'external', or None."
            )

        if len(self.documents) == 0 or self.index.ntotal == 0:
            return []

        # Validate query vector
        q_vec = np.array([query_vector], dtype=np.float32)
        if q_vec.shape[1] != self.dimension:
            raise ValueError(
                f"Query vector dimension mismatch: expected {self.dimension}, got {q_vec.shape[1]}"
            )

        # L2-normalize query vector
        faiss.normalize_L2(q_vec)

        # Search all candidate vectors to enable exact Top-K after metadata filtering
        n_candidates = self.index.ntotal
        scores, indices = self.index.search(q_vec, n_candidates)

        results: List[SearchResult] = []
        rank = 1

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.documents):
                continue

            doc = self.documents[idx]
            doc_source_type = doc.metadata.get("source_type")

            # Apply source_type filter
            if source_type is not None and doc_source_type != source_type:
                continue

            results.append(
                SearchResult(
                    document=doc,
                    score=float(score),
                    rank=rank,
                )
            )
            rank += 1

            if len(results) >= k:
                break

        return results

    def save_local(self, folder_path: Union[str, Path]) -> Path:
        """Persist index and document metadata safely without pickle.

        Args:
            folder_path: Directory path where index files will be stored.

        Returns:
            Path to the directory containing saved files.
        """
        dest_dir = Path(folder_path)
        dest_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save FAISS binary index natively
        index_file = dest_dir / self.INDEX_FILENAME
        faiss.write_index(self.index, str(index_file))

        # 2. Save document chunks and manifest in JSON format
        if self.manifest is None:
            serialized_docs = [
                SerializedDocument(
                    page_content=doc.page_content, metadata=doc.metadata
                )
                for doc in self.documents
            ]
            self.manifest = IndexManifest(
                version="1.0",
                fingerprint=compute_index_fingerprint(self.documents),
                embedding_model="unknown",
                embedding_dimension=self.dimension,
                chunk_size=500,
                chunk_overlap=50,
                total_documents=len(self.documents),
                created_at=datetime.now(timezone.utc).isoformat(),
                documents=serialized_docs,
            )

        docs_file = dest_dir / self.DOCUMENTS_FILENAME
        with open(docs_file, "w", encoding="utf-8") as f:
            f.write(self.manifest.model_dump_json(indent=2))

        return dest_dir

    @classmethod
    def load_local(cls, folder_path: Union[str, Path]) -> "VectorStore":
        """Load persisted index and documents safely from disk without pickle.

        Args:
            folder_path: Directory path where index files are located.

        Returns:
            Loaded VectorStore instance.
        """
        src_dir = Path(folder_path)
        index_file = src_dir / cls.INDEX_FILENAME
        docs_file = src_dir / cls.DOCUMENTS_FILENAME

        if not index_file.exists():
            raise FileNotFoundError(f"FAISS index file not found: {index_file}")
        if not docs_file.exists():
            raise FileNotFoundError(
                f"Documents manifest file not found: {docs_file}"
            )

        # 1. Read FAISS index
        faiss_index = faiss.read_index(str(index_file))

        # 2. Read documents and metadata from JSON
        with open(docs_file, "r", encoding="utf-8") as f:
            raw_json = f.read()

        manifest = IndexManifest.model_validate_json(raw_json)

        documents = [
            Document(page_content=item.page_content, metadata=item.metadata)
            for item in manifest.documents
        ]

        if faiss_index.d != manifest.embedding_dimension:
            raise ValueError(
                f"FAISS index dimension ({faiss_index.d}) does not match manifest embedding dimension ({manifest.embedding_dimension})"
            )

        if faiss_index.ntotal != len(documents):
            raise ValueError(
                f"Index vector count ({faiss_index.ntotal}) does not match document count ({len(documents)})"
            )

        return cls(
            index=faiss_index,
            documents=documents,
            manifest=manifest,
            dimension=manifest.embedding_dimension,
        )
