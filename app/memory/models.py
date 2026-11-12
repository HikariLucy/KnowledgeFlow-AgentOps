"""Memory domain models for KnowledgeFlow Agent."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MemoryRole(str, Enum):
    """Roles supported by short-term conversational memory."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MemoryType(str, Enum):
    """Categories supported by persistent long-term memory."""

    FACT = "fact"
    EVENT = "event"
    SUMMARY = "summary"
    TOOL_RESULT = "tool_result"


class ShortTermMessage(BaseModel):
    """One message retained in the active conversational window."""

    role: MemoryRole
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content cannot be empty or whitespace only")
        return value


class MemoryCreate(BaseModel):
    """Input used to persist one long-term memory."""

    conversation_id: str
    content: str
    memory_type: MemoryType = MemoryType.EVENT
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("conversation_id", "content")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty or whitespace only")
        return value


class MemoryRecord(BaseModel):
    """Persisted long-term memory."""

    id: int
    public_id: str
    conversation_id: str
    content: str
    memory_type: MemoryType
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None
    created_at: datetime


class SemanticMemoryResult(BaseModel):
    """Long-term memory returned by semantic similarity search."""

    memory: MemoryRecord
    score: float = Field(..., ge=-1.0, le=1.0)
