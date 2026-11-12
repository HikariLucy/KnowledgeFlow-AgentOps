"""Manual end-to-end integration test script for full live RAG pipeline with Gemini.

This script runs a real RAG query against the persisted vectorstore using live Gemini APIs.
It is isolated from automated unit tests and never dumps secret keys.
"""

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.agents.source_router import GeminiSourceRouter
from app.core.config import get_settings
from app.llm.client import get_gemini_client
from app.rag.embeddings import GeminiEmbeddings
from app.rag.generator import GeminiRAGGenerator
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import Retriever
from app.rag.vectorstore import VectorStore, verify_index_freshness


def run_live_rag_check() -> None:
    """Execute live end-to-end RAG query."""
    settings = get_settings()
    gemini_client = get_gemini_client(settings)

    if not gemini_client.is_configured:
        print("========================================")
        print("    KnowledgeFlow Live RAG Test         ")
        print("========================================")
        print("Status: SKIPPED")
        print(
            "Reason: GEMINI_API_KEY is not configured in your environment or .env file."
        )
        print("========================================")
        return

    print("========================================")
    print("    KnowledgeFlow Live RAG Test         ")
    print("========================================")
    print(f"Chat Model:    {settings.gemini_chat_model}")
    print(f"Embed Model:   {settings.gemini_embedding_model}")
    print(f"Min Sim Thresh:{settings.rag_min_similarity}")
    print(f"Temperature:   {settings.llm_temperature}")
    print("----------------------------------------")

    vdir = settings.vectorstore_dir
    try:
        vectorstore = VectorStore.load_local(vdir)
    except FileNotFoundError:
        print("Status: FAILED")
        print(f"Reason: Vector store in '{vdir}' not found. Run 'python -m app.rag.indexer' first.")
        sys.exit(1)

    if not vectorstore.manifest or not verify_index_freshness(vectorstore.manifest, settings=settings):
        print("Status: FAILED")
        print("Reason: Vector store is stale. Re-run 'python -m app.rag.indexer'.")
        sys.exit(1)

    embeddings = GeminiEmbeddings(settings=settings, gemini_client=gemini_client)
    retriever = Retriever(vectorstore=vectorstore, embeddings=embeddings, settings=settings)
    router = GeminiSourceRouter(settings=settings, gemini_client=gemini_client)
    generator = GeminiRAGGenerator(settings=settings, gemini_client=gemini_client)

    pipeline = RAGPipeline(
        retriever=retriever,
        router=router,
        generator=generator,
        settings=settings,
    )

    test_query = "¿Qué protocolo debo seguir ante un incidente de seguridad?"
    print(f"Testing Query: {test_query}")

    try:
        answer = pipeline.run(query=test_query)
        print("Status:       SUCCESS")
        print(f"Source Scope: {answer.source_scope}")
        print(f"Abstained:    {answer.abstained}")
        print(f"Citations:    {answer.citations}")
        print(f"Answer:\n{answer.answer}")
        print("========================================")
    except Exception as e:
        print("Status:       ERROR")
        print(f"Pipeline execution failed: {e}")
        print("========================================")
        sys.exit(1)


if __name__ == "__main__":
    run_live_rag_check()
