"""Document chunking pipeline using RecursiveCharacterTextSplitter."""

from typing import List, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings


def validate_chunking_parameters(chunk_size: int, chunk_overlap: int) -> None:
    """Validate that chunking parameters satisfy RAG requirements.

    Args:
        chunk_size: Size of chunks in characters.
        chunk_overlap: Overlap between consecutive chunks.

    Raises:
        ValueError: If parameters are invalid.
    """
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be greater than 0, got {chunk_size}")
    if chunk_overlap < 0:
        raise ValueError(f"chunk_overlap must be non-negative, got {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})"
        )


def split_documents(
    documents: List[Document],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """Split a collection of documents into chunks using RecursiveCharacterTextSplitter.

    Preserves original document metadata and assigns a sequential `chunk_index`
    per source document for end-to-end traceability.

    Args:
        documents: List of input Document objects.
        chunk_size: Optional override for chunk size (defaults to app config).
        chunk_overlap: Optional override for chunk overlap (defaults to app config).

    Returns:
        List of chunked Document objects with preserved and enhanced metadata.
    """
    settings = get_settings()
    resolved_chunk_size = chunk_size if chunk_size is not None else settings.chunk_size
    resolved_chunk_overlap = (
        chunk_overlap if chunk_overlap is not None else settings.chunk_overlap
    )

    validate_chunking_parameters(resolved_chunk_size, resolved_chunk_overlap)

    if not documents:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=resolved_chunk_size,
        chunk_overlap=resolved_chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )

    chunked_documents: List[Document] = []

    # Process documents individually to assign accurate per-document chunk_index
    for doc in documents:
        if not doc.page_content or not doc.page_content.strip():
            continue

        raw_chunks = splitter.split_text(doc.page_content)
        clean_chunks = [c for c in raw_chunks if c.strip()]

        for idx, chunk_text in enumerate(clean_chunks):
            # Create a copy of original metadata to avoid mutating the original
            metadata = dict(doc.metadata)
            metadata["chunk_index"] = idx
            chunked_documents.append(
                Document(page_content=chunk_text, metadata=metadata)
            )

    return chunked_documents
