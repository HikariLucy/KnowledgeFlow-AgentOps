"""Main entrypoint for KnowledgeFlow RAG FastAPI service."""

from pathlib import Path
from contextlib import asynccontextmanager
import asyncio
import sqlite3

from starlette.concurrency import run_in_threadpool
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.api.dashboard_routes import router as dashboard_router
from app.api.agent_routes import router as agent_router
from app.api.observability_routes import router as observability_router
from app.observability.store import EventStore
from app.core.config import get_settings
from app.observability import telemetry
from app.observability.middleware import ObservabilityMiddleware

settings = get_settings()
telemetry.observer = telemetry.Observer(
    enabled=settings.obs_enabled,
    mode=settings.obs_execution_mode,
    session_key=(settings.obs_session_key.get_secret_value().encode()
                 if settings.obs_session_key is not None else None),
)

class ApplicationEventSink:
    """Keep storage failures isolated, without falling back to unbounded stderr."""
    def append(self, event):
        store = app.state.observability_store
        if store is None:
            raise OSError('Observability store unavailable')
        store.append(event)


@asynccontextmanager
async def observability_lifespan(application):
    application.state.observability_settings = settings
    application.state.observability_store = None
    task = None
    if settings.obs_store_enabled:
        telemetry.observer.store = ApplicationEventSink()
        try:
            application.state.observability_store = await run_in_threadpool(
                EventStore, settings.obs_store_path, retention_days=settings.obs_retention_days,
                max_events=settings.obs_max_events, max_bytes=settings.obs_max_bytes)
        except (OSError, ValueError, sqlite3.Error):
            telemetry.observer.dropped_events += 1

        async def maintain():
            while True:
                await asyncio.sleep(60)
                try:
                    store = application.state.observability_store
                    if store is not None:
                        await run_in_threadpool(store.maintain)
                except Exception:
                    telemetry.observer.dropped_events += 1
        task = asyncio.create_task(maintain())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        application.state.observability_store = None


app = FastAPI(
    lifespan=observability_lifespan,
    title=settings.app_name,
    description="Asistente para consulta y recuperación de conocimiento organizacional.",
    version="0.1.0",
)

app.state.observability_settings = settings
app.state.observability_store = None
app.add_middleware(ObservabilityMiddleware)

# Static files directory
UI_STATIC_DIR = Path(__file__).resolve().parent / "ui" / "static"
if UI_STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(UI_STATIC_DIR)), name="static")

# Register API routes
app.include_router(api_router)
app.include_router(agent_router)
app.include_router(observability_router)
app.include_router(dashboard_router)


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
