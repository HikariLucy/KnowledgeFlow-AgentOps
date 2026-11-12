"""Main entrypoint for KnowledgeFlow RAG FastAPI service."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.api.agent_routes import router as agent_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Asistente para consulta y recuperación de conocimiento organizacional.",
    version="0.1.0",
)

# Static files directory
UI_STATIC_DIR = Path(__file__).resolve().parent / "ui" / "static"
if UI_STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(UI_STATIC_DIR)), name="static")

# Register API routes
app.include_router(api_router)
app.include_router(agent_router)


@app.get("/", tags=["UI"], include_in_schema=False)
async def serve_ui():
    """Serve the KnowledgeFlow RAG web user interface."""
    index_file = UI_STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "KnowledgeFlow RAG UI static files not found."}


@app.get("/agent", tags=["UI"], include_in_schema=False)
async def serve_agent_ui():
    """Serve the KnowledgeFlow Agent EP2 workspace."""
    agent_file = UI_STATIC_DIR / "agent.html"
    if agent_file.exists():
        return FileResponse(agent_file)
    return {"message": "KnowledgeFlow Agent UI static files not found."}


@app.get("/health", tags=["Health"])
async def health_check():
    """Service healthcheck endpoint."""
    return {
        "status": "ok",
        "service": settings.app_name,
    }
