"""Offline UI Preview Server for KnowledgeFlow RAG.

This module provides an isolated development entrypoint to visually preview all
UI states, evidence cards, citations, and abstention behavior WITHOUT calling
Google Gemini or touching the live vector index.

Usage:
    python -m uvicorn scripts.ui_preview:app --reload --host 127.0.0.1 --port 8010
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import get_rag_pipeline, router as api_router
from app.core.config import get_settings
from app.rag.schemas import RAGAnswer, SourceScope

logger = logging.getLogger(__name__)

FIXTURES_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "ui_preview_responses.json"
UI_STATIC_DIR = Path(__file__).resolve().parent.parent / "app" / "ui" / "static"


class PreviewRAGPipeline:
    """Mock RAG Pipeline that returns deterministic fixtures for offline UI preview."""

    def __init__(self, fixtures_path: Path = FIXTURES_PATH):
        self.fixtures = self._load_fixtures(fixtures_path)

    @staticmethod
    def _load_fixtures(path: Path) -> Dict[str, Any]:
        """Load fixture JSON file safely."""
        if not path.exists():
            logger.warning("Preview fixtures file not found at '%s'. Using empty dict.", path)
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("scenarios", {})

    def run(
        self,
        query: str,
        source_scope: Optional[SourceScope] = None,
        top_k: Optional[int] = None,
    ) -> RAGAnswer:
        """Route incoming query to corresponding fixture scenario."""
        q_lower = query.lower().strip()

        # Error state triggers for UI development
        if "preview_error_500" in q_lower:
            raise RuntimeError("Simulated internal server error (HTTP 500) for UI preview.")
        if "preview_error_503" in q_lower:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Simulated index unavailable error (HTTP 503) for UI preview.",
            )

        # Scenario D: Abstention
        if any(term in q_lower for term in ["velocidad de la luz", "luz en el vacío", "cuántica", "capital de"]):
            fixture = self.fixtures.get("abstention", {})
            return RAGAnswer(
                query=query,
                source_scope=source_scope or fixture.get("source_scope", "all"),
                answer=fixture.get("answer", "No encontré evidencia documental suficiente."),
                citations=fixture.get("citations", []),
                sources=fixture.get("sources", []),
                abstained=True,
            )

        # Scenario E: High Citation Density (4 sources, 4 citations)
        if any(term in q_lower for term in ["densidad", "auditoría", "completa", "integral"]):
            fixture = self.fixtures.get("density", {})
            return RAGAnswer(
                query=query,
                source_scope=source_scope or fixture.get("source_scope", "all"),
                answer=fixture.get("answer", ""),
                citations=fixture.get("citations", []),
                sources=fixture.get("sources", []),
                abstained=False,
            )

        # Scenario A: Internal
        if source_scope == "internal" or any(term in q_lower for term in ["contraseña", "requisito", "novatech", "vacaciones", "accesos"]):
            fixture = self.fixtures.get("internal", {})
            return RAGAnswer(
                query=query,
                source_scope="internal",
                answer=fixture.get("answer", ""),
                citations=fixture.get("citations", []),
                sources=fixture.get("sources", []),
                abstained=False,
            )

        # Scenario B: External
        if source_scope == "external" or any(term in q_lower for term in ["prompt injection", "owasp", "nist", "ssdf", "externo", "estándar"]):
            fixture = self.fixtures.get("external", {})
            return RAGAnswer(
                query=query,
                source_scope="external",
                answer=fixture.get("answer", ""),
                citations=fixture.get("citations", []),
                sources=fixture.get("sources", []),
                abstained=False,
            )

        # Scenario C: Mixed / All (Default for comparative and general queries)
        fixture = self.fixtures.get("mixed", {})
        return RAGAnswer(
            query=query,
            source_scope=source_scope or "all",
            answer=fixture.get("answer", ""),
            citations=fixture.get("citations", []),
            sources=fixture.get("sources", []),
            abstained=False,
        )


def create_preview_app() -> FastAPI:
    """Create an isolated FastAPI application instance configured for offline UI preview."""
    settings = get_settings()

    preview_app = FastAPI(
        title=f"{settings.app_name} (UI Preview)",
        description="Offline UI Preview Server with deterministic fixtures (Zero Gemini API calls).",
        version="0.1.0-preview",
    )

    # Mount UI static files
    if UI_STATIC_DIR.exists():
        preview_app.mount("/static", StaticFiles(directory=str(UI_STATIC_DIR)), name="static")

    # Mount API routes
    preview_app.include_router(api_router)

    # Set up dependency override ONLY on this preview_app instance
    preview_pipeline = PreviewRAGPipeline()
    preview_app.dependency_overrides[get_rag_pipeline] = lambda: preview_pipeline

    @preview_app.get("/", tags=["UI"], include_in_schema=False)
    async def serve_ui():
        index_file = UI_STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "KnowledgeFlow RAG UI static files not found."}

    @preview_app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "ok",
            "service": f"{settings.app_name} (UI Preview)",
            "mode": "preview_offline",
        }

    return preview_app


# Top-level ASGI app for uvicorn (e.g. uvicorn scripts.ui_preview:app)
app = create_preview_app()
