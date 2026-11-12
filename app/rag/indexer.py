"""CLI entrypoint to load, chunk, embed, and index knowledge base into FAISS."""

import sys
from pathlib import Path
from typing import Optional

from app.core.config import Settings, get_settings
from app.rag.chunking import split_documents
from app.rag.embeddings import BaseEmbeddings, GeminiEmbeddings
from app.rag.loaders import load_knowledge_base
from app.rag.vectorstore import VectorStore


def run_indexer(
    knowledge_dir: str = "knowledge",
    output_dir: Optional[str] = None,
    embeddings_provider: Optional[BaseEmbeddings] = None,
    settings: Optional[Settings] = None,
) -> VectorStore:
    """Execute full knowledge base ingestion, chunking, embedding and indexing pipeline.

    Args:
        knowledge_dir: Directory path containing internal/external subdirectories.
        output_dir: Destination folder for persisting FAISS vectorstore.
        embeddings_provider: Optional custom embeddings provider.
        settings: Application settings.

    Returns:
        Built and persisted VectorStore instance.
    """
    cfg = settings or get_settings()
    target_output_dir = output_dir or cfg.vectorstore_dir
    provider = embeddings_provider or GeminiEmbeddings(settings=cfg)

    print("========================================")
    print("      KnowledgeFlow RAG Indexer         ")
    print("========================================")

    # 1. Load documents
    print(f"Loading documents from: '{knowledge_dir}'...")
    raw_docs = load_knowledge_base(knowledge_dir)
    print(f"Documents loaded: {len(raw_docs)}")

    if not raw_docs:
        print("Warning: No valid documents found to index.")
        return VectorStore.from_documents([], [], settings=cfg)

    # 2. Split into chunks
    print(
        f"Splitting documents (chunk_size={cfg.chunk_size}, chunk_overlap={cfg.chunk_overlap})..."
    )
    chunks = split_documents(
        raw_docs,
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
    )
    print(f"Chunks generated: {len(chunks)}")

    internal_count = sum(
        1 for c in chunks if c.metadata.get("source_type") == "internal"
    )
    external_count = sum(
        1 for c in chunks if c.metadata.get("source_type") == "external"
    )

    # 3. Generate embeddings
    print(
        f"Generating embeddings via model '{cfg.gemini_embedding_model}' (dim={cfg.embedding_dimension})..."
    )
    embeddings = provider.embed_documents(chunks)
    print(f"Embeddings generated: {len(embeddings)}")

    # 4. Build FAISS vector store
    print("Building FAISS index (Inner Product / Cosine Similarity)...")
    vectorstore = VectorStore.from_documents(
        documents=chunks,
        embeddings=embeddings,
        settings=cfg,
    )

    # 5. Persist to disk
    saved_path = vectorstore.save_local(target_output_dir)
    print(f"Index saved to: '{saved_path.resolve()}'")

    print("----------------------------------------")
    print(f"Total Chunks:       {len(chunks)}")
    print(f"Internal Chunks:    {internal_count}")
    print(f"External Chunks:    {external_count}")
    print(f"Embedding Dim:      {cfg.embedding_dimension}")
    print(f"Index Fingerprint:  {vectorstore.manifest.fingerprint[:16]}...")
    print("========================================")
    print("Indexing completed successfully.")

    return vectorstore


def main() -> None:
    """CLI main function."""
    try:
        run_indexer()
    except Exception as e:
        print(f"Error during indexing: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
