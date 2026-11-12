"""Manual integration test script for Gemini Embedding 2.

This script tests live connectivity to Google Gemini Embedding API when GEMINI_API_KEY is configured.
It is isolated from automated unit tests and never dumps secret keys or raw vector values.
"""

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.config import get_settings
from app.llm.client import get_gemini_client
from app.rag.embeddings import GeminiEmbeddings


def run_live_embedding_check() -> None:
    """Execute a real embedding call against Gemini Embedding API."""
    settings = get_settings()
    gemini_client = get_gemini_client(settings)

    if not gemini_client.is_configured:
        print("========================================")
        print("  Gemini Live Embedding Verification    ")
        print("========================================")
        print("Status: SKIPPED")
        print(
            "Reason: GEMINI_API_KEY is not configured in your environment or .env file."
        )
        print(
            "To test live Gemini embeddings, please configure GEMINI_API_KEY in .env and rerun this script."
        )
        print("========================================")
        return

    print("========================================")
    print("  Gemini Live Embedding Verification    ")
    print("========================================")
    print(f"Model:     {settings.gemini_embedding_model}")
    print(f"Dimension: {settings.embedding_dimension}")

    try:
        provider = GeminiEmbeddings(settings=settings, gemini_client=gemini_client)
        test_text = "Prueba de conectividad y generación de embeddings para KnowledgeFlow RAG."
        vector = provider.embed_query(test_text)

        if len(vector) != settings.embedding_dimension:
            print("Status: FAILED")
            print(
                f"Dimension mismatch: Expected {settings.embedding_dimension}, received {len(vector)}"
            )
            sys.exit(1)

        print("Status:    SUCCESS")
        print("Embedding generated and dimension verified successfully.")
        print("========================================")

    except Exception as e:
        print("Status:    ERROR")
        print(f"Failed to generate embedding: {e}")
        print("========================================")
        sys.exit(1)


if __name__ == "__main__":
    run_live_embedding_check()
