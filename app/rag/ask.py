"""CLI demonstration tool for end-to-end RAG answer generation and citation tracking."""

import argparse
import sys
from typing import Optional

from app.agents.source_router import BaseSourceRouter, GeminiSourceRouter
from app.core.config import Settings, get_settings
from app.rag.embeddings import BaseEmbeddings, GeminiEmbeddings
from app.rag.generator import BaseRAGGenerator, GeminiRAGGenerator
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import Retriever
from app.rag.schemas import SourceScope
from app.rag.vectorstore import VectorStore, verify_index_freshness


def run_ask(
    query: str,
    source_scope: Optional[SourceScope] = None,
    k: Optional[int] = None,
    vectorstore_dir: Optional[str] = None,
    knowledge_dir: str = "knowledge",
    router: Optional[BaseSourceRouter] = None,
    embeddings_provider: Optional[BaseEmbeddings] = None,
    generator: Optional[BaseRAGGenerator] = None,
    settings: Optional[Settings] = None,
    enforce_freshness: bool = True,
) -> None:
    """Execute end-to-end RAG query and print formatted answer and source citations."""
    cfg = settings or get_settings()
    vdir = vectorstore_dir or cfg.vectorstore_dir

    try:
        vectorstore = VectorStore.load_local(vdir)
    except FileNotFoundError as e:
        print(
            f"Error: Vector store not found in '{vdir}'. Run 'python -m app.rag.indexer' first.\n({e})",
            file=sys.stderr,
        )
        sys.exit(1)

    if enforce_freshness:
        if not vectorstore.manifest or not verify_index_freshness(
            vectorstore.manifest,
            knowledge_dir=knowledge_dir,
            settings=cfg,
        ):
            print(
                "Error: Vector index is stale. Re-run: python -m app.rag.indexer",
                file=sys.stderr,
            )
            sys.exit(1)

    embed_provider = embeddings_provider or GeminiEmbeddings(settings=cfg)
    retriever = Retriever(
        vectorstore=vectorstore, embeddings=embed_provider, settings=cfg
    )
    router_agent = router or GeminiSourceRouter(settings=cfg)
    rag_generator = generator or GeminiRAGGenerator(settings=cfg)

    pipeline = RAGPipeline(
        retriever=retriever,
        router=router_agent,
        generator=rag_generator,
        settings=cfg,
    )

    answer = pipeline.run(
        query=query,
        source_scope=source_scope,
        top_k=k,
    )

    print("========================================")
    print("      KnowledgeFlow RAG Assistant       ")
    print("========================================")
    print(f"Query:        {answer.query}")
    print(f"Source Scope: {answer.source_scope}")
    print(f"Abstained:    {answer.abstained}")
    print("----------------------------------------")
    print(f"Answer:\n{answer.answer}\n")

    if answer.citations:
        print(f"Citations:    {', '.join(answer.citations)}")
    else:
        print("Citations:    None")

    print("\nRetrieved Evidence Sources:")
    if not answer.sources:
        print("  (No sources met the similarity threshold)")
    else:
        for src in answer.sources:
            print(
                f"  [{src.id}] File: {src.file_name} | Type: {src.source_type} | "
                f"Score: {src.score:.4f} | Chunk: {src.chunk_index if src.chunk_index is not None else 'N/A'}"
            )
    print("========================================\n")


def main() -> None:
    """CLI argument parser for python -m app.rag.ask."""
    parser = argparse.ArgumentParser(
        description="Query KnowledgeFlow RAG with Grounded Generation and Routing"
    )
    parser.add_argument(
        "query",
        type=str,
        help="User question or query",
    )
    parser.add_argument(
        "-s",
        "--source-scope",
        type=str,
        choices=["internal", "external", "all"],
        default=None,
        help="Manual source scope override: 'internal', 'external', or 'all'",
    )
    parser.add_argument(
        "-k",
        "--top-k",
        type=int,
        default=None,
        help="Number of Top-K results to retrieve (default: from config)",
    )
    parser.add_argument(
        "-v",
        "--vectorstore-dir",
        type=str,
        default=None,
        help="Custom vector store directory",
    )
    parser.add_argument(
        "-d",
        "--knowledge-dir",
        type=str,
        default="knowledge",
        help="Knowledge base directory to verify freshness against",
    )

    args = parser.parse_args()

    try:
        run_ask(
            query=args.query,
            source_scope=args.source_scope,
            k=args.top_k,
            vectorstore_dir=args.vectorstore_dir,
            knowledge_dir=args.knowledge_dir,
        )
    except Exception as e:
        print(f"Error during RAG generation: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
