"""Operational incident specialist agent."""

from app.agents.profile import AgentProfile
from app.storage.models import (
    Incident,
    IncidentNote,
)
from app.tools.incidents import (
    AppendIncidentNoteTool,
    CreateIncidentTool,
    SearchIncidentsTool,
)
from app.tools.schemas import (
    AppendIncidentNoteInput,
    CreateIncidentInput,
    SearchIncidentsInput,
)


OPERATIONS_AGENT_PROFILE = AgentProfile(
    name="operations_agent",
    role="Operations Agent",
    goal=(
        "Gestionar incidentes organizacionales mediante operaciones "
        "validadas, controladas y trazables."
    ),
    backstory=(
        "Especialista operacional de KnowledgeFlow Agent. Puede consultar "
        "y escribir incidentes, pero no consulta directamente el RAG."
    ),
    allow_delegation=False,
    tools=(
        "create_incident",
        "search_incidents",
        "append_incident_note",
    ),
)


class OperationsAgent:
    """Specialist restricted to validated incident operations."""

    profile = OPERATIONS_AGENT_PROFILE

    def __init__(
        self,
        create_incident_tool: CreateIncidentTool,
        search_incidents_tool: SearchIncidentsTool,
        append_incident_note_tool: AppendIncidentNoteTool,
    ) -> None:
        self.create_incident_tool = create_incident_tool
        self.search_incidents_tool = search_incidents_tool
        self.append_incident_note_tool = append_incident_note_tool

    def create_incident(
        self,
        arguments: CreateIncidentInput,
    ) -> Incident:
        """Create one validated incident."""
        return self.create_incident_tool.run(arguments)

    def search_incidents(
        self,
        arguments: SearchIncidentsInput,
    ) -> list[Incident]:
        """Search persisted incidents."""
        return self.search_incidents_tool.run(arguments)

    def append_incident_note(
        self,
        arguments: AppendIncidentNoteInput,
    ) -> IncidentNote:
        """Append validated follow-up information."""
        return self.append_incident_note_tool.run(arguments)
