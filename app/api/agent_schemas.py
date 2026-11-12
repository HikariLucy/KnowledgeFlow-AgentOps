"""Typed HTTP contracts for the KnowledgeFlow agent endpoint."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.agentic.orchestrator import ExecutionStatus
from app.tools.schemas import (
    AppendIncidentNoteDraft,
    CreateIncidentInput,
    KnowledgeQueryInput,
    SearchIncidentsInput,
)


class AgentRequest(BaseModel):
    """One user turn submitted to the agentic runtime."""

    conversation_id: str = Field(
        ...,
        description="Stable conversation identifier used for memory continuity.",
    )
    message: str = Field(
        ...,
        description="Natural-language request for the organizational agent.",
    )

    knowledge_query: KnowledgeQueryInput | None = None
    create_incident: CreateIncidentInput | None = None
    search_incidents: SearchIncidentsInput | None = None
    append_incident_note: AppendIncidentNoteDraft | None = None

    @field_validator("conversation_id", "message")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty or whitespace only")
        return value


class AgentResponse(BaseModel):
    """Structured, UI-ready result of one agentic execution."""

    status: ExecutionStatus
    conversation_id: str
    intent: str | None = None

    plan: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    tool_calls: list[str] = Field(default_factory=list)
    completed_steps: list[str] = Field(default_factory=list)

    memory_context: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    observations: list[dict[str, Any]] = Field(default_factory=list)

    incident_id: str | None = None
    requires_clarification: bool = False
    clarification_question: str | None = None

    iteration_count: int = 0
    output: str | None = None
