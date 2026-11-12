"""FastAPI API routes for KnowledgeFlow RAG query endpoint."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.rag.embeddings import GeminiEmbeddings
from app.rag.generator import GeminiRAGGenerator
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import Retriever
from app.rag.schemas import QueryRequest, QueryResponse
from app.rag.vectorstore import VectorStore, verify_index_freshness
from app.agents.source_router import GeminiSourceRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["RAG"])

# In-memory cached pipeline singleton
_cached_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline(
    settings: Settings = Depends(get_settings),
) -> RAGPipeline:
    """Dependency provider for RAGPipeline with vectorstore freshness verification.

    Raises:
        HTTPException 503: If vector store is missing, invalid, or stale.
    """
    global _cached_pipeline

    if _cached_pipeline is not None:
        return _cached_pipeline

    vdir = settings.vectorstore_dir
    try:
        vectorstore = VectorStore.load_local(vdir)
    except Exception as e:
        logger.error("Failed to load vectorstore from '%s': %s", vdir, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store is not available or is stale. Run: python -m app.rag.indexer",
        ) from e

    # Validate freshness against current corpus and configuration
    if not vectorstore.manifest or not verify_index_freshness(
        vectorstore.manifest,
        knowledge_dir="knowledge",
        settings=settings,
    ):
        logger.warning("Vectorstore manifest in '%s' is stale.", vdir)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store is not available or is stale. Run: python -m app.rag.indexer",
        )

    embeddings = GeminiEmbeddings(settings=settings)
    retriever = Retriever(
        vectorstore=vectorstore, embeddings=embeddings, settings=settings
    )
    router_agent = GeminiSourceRouter(settings=settings)
    generator = GeminiRAGGenerator(settings=settings)

    _cached_pipeline = RAGPipeline(
        retriever=retriever,
        router=router_agent,
        generator=generator,
        settings=settings,
    )
    return _cached_pipeline


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query KnowledgeFlow RAG System",
    description="Submit a question to the RAG pipeline for source routing, semantic retrieval, and grounded generation.",
)
async def query_rag(
    request: QueryRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> QueryResponse:
    """Process query through RAG pipeline and return grounded response with citations."""
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query string cannot be empty or whitespace only.",
        )

    try:
        answer = pipeline.run(
            query=request.query,
            source_scope=request.source_scope,
            top_k=request.k,
        )
        return QueryResponse(**answer.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error executing RAG pipeline: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your query.",
        ) from e
