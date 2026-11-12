"""RAG module for document loading, preprocessing, chunking, embeddings, retrieval, prompt engineering and generation."""

from app.rag.chunking import split_documents, validate_chunking_parameters
from app.rag.context import (
    build_rag_context,
    extract_citations_from_text,
    validate_citations,
)
from app.rag.embeddings import (
    BaseEmbeddings,
    DeterministicFakeEmbeddings,
    GeminiEmbeddings,
    get_document_title,
    prepare_document_for_embedding,
    prepare_query_for_embedding,
)
from app.rag.generator import (
    BaseRAGGenerator,
    FakeRAGGenerator,
    GeminiRAGGenerator,
)
from app.rag.loaders import (
    infer_source_type,
    load_directory,
    load_document,
    load_knowledge_base,
)
from app.rag.pipeline import RAGPipeline
from app.rag.prompts import RAG_SYSTEM_PROMPT, format_rag_user_prompt
from app.rag.retriever import Retriever
from app.rag.schemas import (
    DocumentMetadata,
    IndexManifest,
    QueryRequest,
    QueryResponse,
    RAGAnswer,
    RouteDecision,
    SearchResult,
    SerializedDocument,
    SourceReference,
    SourceScope,
    SourceType,
)
from app.rag.vectorstore import (
    VectorStore,
    compute_index_fingerprint,
    validate_index_fingerprint,
    verify_index_freshness,
)

__all__ = [
    "load_document",
    "load_directory",
    "load_knowledge_base",
    "infer_source_type",
    "split_documents",
    "validate_chunking_parameters",
    "DocumentMetadata",
    "SourceType",
    "SourceScope",
    "SearchResult",
    "SerializedDocument",
    "IndexManifest",
    "RouteDecision",
    "SourceReference",
    "RAGAnswer",
    "QueryRequest",
    "QueryResponse",
    "BaseEmbeddings",
    "GeminiEmbeddings",
    "DeterministicFakeEmbeddings",
    "get_document_title",
    "prepare_document_for_embedding",
    "prepare_query_for_embedding",
    "VectorStore",
    "compute_index_fingerprint",
    "validate_index_fingerprint",
    "verify_index_freshness",
    "Retriever",
    "build_rag_context",
    "extract_citations_from_text",
    "validate_citations",
    "RAG_SYSTEM_PROMPT",
    "format_rag_user_prompt",
    "BaseRAGGenerator",
    "GeminiRAGGenerator",
    "FakeRAGGenerator",
    "RAGPipeline",
]
