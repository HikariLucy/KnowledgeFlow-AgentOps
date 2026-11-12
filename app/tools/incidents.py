"""Operational incident tools for KnowledgeFlow Agent."""

from app.storage.models import (
    Incident,
    IncidentCreate,
    IncidentNote,
    IncidentNoteCreate,
)
from app.storage.repositories import IncidentRepository
from app.tools.schemas import (
    AppendIncidentNoteInput,
    CreateIncidentInput,
    SearchIncidentsInput,
)


class CreateIncidentTool:
    """Create a validated organizational incident."""

    name = "create_incident"

    description = (
        "Registra un nuevo incidente organizacional cuando existe información "
        "suficiente sobre el problema, su categoría y severidad."
    )

    def __init__(self, repository: IncidentRepository) -> None:
        self.repository = repository

    def run(self, arguments: CreateIncidentInput) -> Incident:
        """Validate and persist a new incident."""
        return self.repository.create_incident(
            IncidentCreate(
                title=arguments.title,
                description=arguments.description,
                category=arguments.category,
                severity=arguments.severity,
            )
        )


class SearchIncidentsTool:
    """Search previously persisted organizational incidents."""

    name = "search_incidents"

    description = (
        "Busca incidentes registrados previamente mediante texto, "
        "identificador o estado."
    )

    def __init__(self, repository: IncidentRepository) -> None:
        self.repository = repository

    def run(self, arguments: SearchIncidentsInput) -> list[Incident]:
        """Return incidents matching the validated filters."""
        return self.repository.search_incidents(
            query=arguments.query,
            status=arguments.status,
            limit=arguments.limit,
        )


class AppendIncidentNoteTool:
    """Append follow-up information to an existing incident."""

    name = "append_incident_note"

    description = (
        "Agrega información de seguimiento a un incidente existente "
        "sin modificar ni eliminar su historial previo."
    )

    def __init__(self, repository: IncidentRepository) -> None:
        self.repository = repository

    def run(self, arguments: AppendIncidentNoteInput) -> IncidentNote:
        """Persist a follow-up note for an existing incident."""
        return self.repository.append_note(
            incident_public_id=arguments.incident_id,
            data=IncidentNoteCreate(note=arguments.note),
        )
