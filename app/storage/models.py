"""Domain models for KnowledgeFlow Agent operational storage."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class IncidentCategory(str, Enum):
    """Supported organizational incident categories."""

    ACCESS = "access"
    SECURITY = "security"
    HARDWARE = "hardware"
    SOFTWARE = "software"
    OTHER = "other"


class IncidentSeverity(str, Enum):
    """Supported incident severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    """Lifecycle states supported by an incident."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentCreate(BaseModel):
    """Validated domain input used to create an incident."""

    title: str
    description: str
    category: IncidentCategory
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.OPEN

    @field_validator("title", "description")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty or whitespace only")
        return value


class Incident(BaseModel):
    """Persisted incident."""

    id: int
    public_id: str
    title: str
    description: str
    category: IncidentCategory
    severity: IncidentSeverity
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime


class IncidentNoteCreate(BaseModel):
    """Validated input for an incident follow-up note."""

    note: str

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("note cannot be empty or whitespace only")
        return value


class IncidentNote(BaseModel):
    """Persisted incident note."""

    id: int
    incident_public_id: str
    note: str
    created_at: datetime
