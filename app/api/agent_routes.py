"""FastAPI endpoint for the KnowledgeFlow agentic runtime."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.agentic.orchestrator import AdaptiveOrchestrator
from app.agentic.planner import RuleBasedPlanner
from app.agentic.service import AgentService
from app.api.agent_schemas import AgentRequest, AgentResponse
from app.api.routes import get_rag_pipeline
from app.core.config import Settings, get_settings
from app.memory.long_term import LongTermMemoryStore
from app.memory.semantic import SemanticMemory
from app.memory.short_term import ShortTermMemory
from app.memory.write_back import MemoryWriteBack
from app.rag.embeddings import GeminiEmbeddings
from app.rag.pipeline import RAGPipeline
from app.storage.database import SQLiteDatabase
from app.storage.repositories import IncidentRepository
from app.tools.incidents import (
    AppendIncidentNoteTool,
    CreateIncidentTool,
    SearchIncidentsTool,
)
from app.tools.knowledge import KnowledgeRAGTool


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Agent"])

_cached_agent_service: Optional[AgentService] = None


def get_agent_service(
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
    settings: Settings = Depends(get_settings),
) -> AgentService:
    """Build and cache the process-local agent runtime."""
    global _cached_agent_service

    if _cached_agent_service is not None:
        return _cached_agent_service

    database = SQLiteDatabase()
    database.initialize()

    repository = IncidentRepository(database)

    short_term_memory = ShortTermMemory(max_turns=10)
    long_term_store = LongTermMemoryStore(database)
    semantic_memory = SemanticMemory(
        store=long_term_store,
        embeddings=GeminiEmbeddings(settings=settings),
    )

    memory_write_back = MemoryWriteBack(
        short_term_memory=short_term_memory,
        semantic_memory=semantic_memory,
    )

    planner = RuleBasedPlanner(
        short_term_memory=short_term_memory,
        semantic_memory=semantic_memory,
    )

    orchestrator = AdaptiveOrchestrator(
        planner=planner,
        knowledge_tool=KnowledgeRAGTool(pipeline),
        create_incident_tool=CreateIncidentTool(repository),
        search_incidents_tool=SearchIncidentsTool(repository),
        append_incident_note_tool=AppendIncidentNoteTool(repository),
        memory_write_back=memory_write_back,
    )

    _cached_agent_service = AgentService(orchestrator)
    return _cached_agent_service


@router.post(
    "/agent",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute KnowledgeFlow Agent",
    description=(
        "Execute one agentic turn with planning, tools, memory, "
        "operational persistence and structured trace output."
    ),
)
async def execute_agent(
    request: AgentRequest,
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """Execute one validated agent request."""
    try:
        return service.execute(request)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error executing agent workflow: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while executing the agent workflow.",
        ) from exc
