"""Typed tool schemas for KnowledgeFlow Agent Function Calling."""

from pydantic import BaseModel, Field, field_validator

from app.rag.schemas import SourceScope, SourceType
from app.storage.models import (
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
)


class CreateIncidentInput(BaseModel):
    """Arguments accepted by the create_incident tool."""

    title: str = Field(
        ...,
        description="Short descriptive title for the organizational incident",
    )
    description: str = Field(
        ...,
        description="Factual description of the reported problem",
    )
    category: IncidentCategory = Field(
        ...,
        description="Incident category",
    )
    severity: IncidentSeverity = Field(
        ...,
        description="Estimated incident severity",
    )

    @field_validator("title", "description")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty or whitespace only")
        return value


class SearchIncidentsInput(BaseModel):
    """Arguments accepted by the search_incidents tool."""

    query: str | None = Field(
        default=None,
        description="Optional text to find in title, description or incident ID",
    )
    status: IncidentStatus | None = Field(
        default=None,
        description="Optional incident-status filter",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of incidents to return",
    )


class AppendIncidentNoteDraft(BaseModel):
    """Follow-up note whose incident can be resolved from workflow memory."""

    incident_id: str | None = Field(
        default=None,
        description=(
            "Optional public incident identifier. When omitted, the "
            "orchestrator must resolve it from validated workflow context "
            "before invoking the write tool."
        ),
    )
    note: str = Field(
        ...,
        description="Follow-up information to append to the incident",
    )

    @field_validator("incident_id")
    @classmethod
    def validate_optional_incident_id(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()
        if not value:
            raise ValueError("incident_id cannot be whitespace only")
        return value

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("note cannot be empty or whitespace only")
        return value


class AppendIncidentNoteInput(BaseModel):
    """Arguments accepted by the append_incident_note tool."""

    incident_id: str = Field(
        ...,
        description="Public incident identifier such as INC-00001",
    )
    note: str = Field(
        ...,
        description="Follow-up information to append to the incident",
    )

    @field_validator("incident_id", "note")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty or whitespace only")
        return value


class KnowledgeQueryInput(BaseModel):
    """Arguments accepted by the search_knowledge tool."""

    query: str = Field(
        ...,
        description="Question to answer using the organizational knowledge base",
    )
    source_scope: SourceScope | None = Field(
        default=None,
        description=(
            "Optional source restriction: internal, external or all. "
            "When omitted, the existing source router decides."
        ),
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Optional maximum number of evidence chunks to retrieve",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query cannot be empty or whitespace only")
        return value


class KnowledgeSource(BaseModel):
    """Evidence source exposed by the knowledge tool."""

    id: str
    file_name: str
    source_type: SourceType
    chunk_index: int | None = None
    score: float


class KnowledgeQueryResult(BaseModel):
    """Structured result returned to an agent after a RAG consultation."""

    query: str
    source_scope: SourceScope
    answer: str
    citations: list[str] = Field(default_factory=list)
    sources: list[KnowledgeSource] = Field(default_factory=list)
    abstained: bool = False
