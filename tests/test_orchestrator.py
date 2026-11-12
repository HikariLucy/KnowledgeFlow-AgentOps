"""Tests for adaptive KnowledgeFlow orchestration."""

import pytest

from app.agentic.orchestrator import (
    AdaptiveOrchestrator,
    ExecutionStatus,
)
from app.agentic.planner import RuleBasedPlanner
from app.agentic.state import AgentState
from app.storage.database import SQLiteDatabase
from app.storage.repositories import IncidentRepository
from app.tools.incidents import (
    AppendIncidentNoteTool,
    CreateIncidentTool,
    SearchIncidentsTool,
)
from app.tools.schemas import (
    AppendIncidentNoteDraft,
    AppendIncidentNoteInput,
    CreateIncidentInput,
    KnowledgeQueryResult,
    KnowledgeSource,
    SearchIncidentsInput,
)


class StubKnowledgeTool:
    """Deterministic knowledge tool double."""

    name = "search_knowledge"

    def __init__(
        self,
        *,
        abstained: bool = False,
    ) -> None:
        self.abstained = abstained
        self.calls = []

    def run(self, arguments):
        self.calls.append(arguments)

        if self.abstained:
            return KnowledgeQueryResult(
                query=arguments.query,
                source_scope="internal",
                answer="No encontré evidencia suficiente.",
                citations=[],
                sources=[],
                abstained=True,
            )

        return KnowledgeQueryResult(
            query=arguments.query,
            source_scope="internal",
            answer="Procedimiento recuperado [S1].",
            citations=["S1"],
            sources=[
                KnowledgeSource(
                    id="S1",
                    file_name="procedimiento.md",
                    source_type="internal",
                    chunk_index=0,
                    score=0.92,
                )
            ],
            abstained=False,
        )


@pytest.fixture
def operational_tools(tmp_path):
    database = SQLiteDatabase(
        tmp_path / "orchestrator.db"
    )
    database.initialize()

    repository = IncidentRepository(database)

    return {
        "repository": repository,
        "create": CreateIncidentTool(repository),
        "search": SearchIncidentsTool(repository),
        "append": AppendIncidentNoteTool(repository),
    }


def _state(request: str) -> AgentState:
    return AgentState(
        conversation_id="conv-1",
        user_request=request,
    )


def _incident_input() -> CreateIncidentInput:
    return CreateIncidentInput(
        title="Pérdida de autenticador MFA",
        description=(
            "Usuario perdió el dispositivo "
            "utilizado para MFA."
        ),
        category="access",
        severity="medium",
    )


def test_orchestrator_executes_knowledge_query(
    operational_tools,
):
    knowledge = StubKnowledgeTool()

    orchestrator = AdaptiveOrchestrator(
        planner=RuleBasedPlanner(),
        knowledge_tool=knowledge,
        create_incident_tool=operational_tools["create"],
        search_incidents_tool=operational_tools["search"],
        append_incident_note_tool=operational_tools["append"],
    )

    result = orchestrator.execute(
        _state(
            "¿Qué requisitos debe cumplir una contraseña?"
        )
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.state.tool_calls == [
        "search_knowledge"
    ]
    assert len(result.state.retrieved_context) == 1
    assert result.output == (
        "Procedimiento recuperado [S1]."
    )


def test_orchestrator_abstention_blocks_incident_write(
    operational_tools,
):
    orchestrator = AdaptiveOrchestrator(
        planner=RuleBasedPlanner(),
        knowledge_tool=StubKnowledgeTool(
            abstained=True
        ),
        create_incident_tool=operational_tools["create"],
        search_incidents_tool=operational_tools["search"],
        append_incident_note_tool=operational_tools["append"],
    )

    state = _state(
        "Perdí mi autenticador. "
        "Revisa el procedimiento y registra un incidente."
    )

    result = orchestrator.execute(
        state,
        tool_inputs={
            "create_incident": _incident_input(),
        },
    )

    assert result.status == ExecutionStatus.ABSTAINED
    assert result.state.tool_calls == [
        "search_knowledge"
    ]

    incidents = operational_tools[
        "repository"
    ].search_incidents()

    assert incidents == []


def test_orchestrator_creates_incident_after_grounded_knowledge(
    operational_tools,
):
    orchestrator = AdaptiveOrchestrator(
        planner=RuleBasedPlanner(),
        knowledge_tool=StubKnowledgeTool(),
        create_incident_tool=operational_tools["create"],
        search_incidents_tool=operational_tools["search"],
        append_incident_note_tool=operational_tools["append"],
    )

    result = orchestrator.execute(
        _state(
            "Perdí mi autenticador. "
            "Revisa el procedimiento y registra un incidente."
        ),
        tool_inputs={
            "create_incident": _incident_input(),
        },
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.state.tool_calls == [
        "search_knowledge",
        "create_incident",
    ]
    assert result.state.incident_id == "INC-00001"
    assert result.output == (
        "Procedimiento recuperado [S1].\n\n"
        "Incidente creado: INC-00001."
    )

    assert (
        "Validar información mínima del incidente"
        in result.state.completed_steps
    )
    assert (
        "Crear incidente"
        in result.state.completed_steps
    )


def test_orchestrator_requires_payload_before_incident_write(
    operational_tools,
):
    orchestrator = AdaptiveOrchestrator(
        planner=RuleBasedPlanner(),
        knowledge_tool=StubKnowledgeTool(),
        create_incident_tool=operational_tools["create"],
        search_incidents_tool=operational_tools["search"],
        append_incident_note_tool=operational_tools["append"],
    )

    result = orchestrator.execute(
        _state(
            "Revisa el procedimiento "
            "y registra un incidente."
        )
    )

    assert (
        result.status
        == ExecutionStatus.NEEDS_CLARIFICATION
    )
    assert result.state.tool_calls == [
        "search_knowledge"
    ]
    assert result.state.requires_clarification is True

    assert (
        operational_tools[
            "repository"
        ].search_incidents()
        == []
    )


def test_orchestrator_searches_incidents(
    operational_tools,
):
    operational_tools["create"].run(
        CreateIncidentInput(
            title="Error de acceso VPN",
            description="Usuario sin acceso a VPN.",
            category="access",
            severity="medium",
        )
    )

    orchestrator = AdaptiveOrchestrator(
        planner=RuleBasedPlanner(),
        knowledge_tool=StubKnowledgeTool(),
        create_incident_tool=operational_tools["create"],
        search_incidents_tool=operational_tools["search"],
        append_incident_note_tool=operational_tools["append"],
    )

    result = orchestrator.execute(
        _state(
            "Busca los incidentes relacionados con VPN."
        ),
        tool_inputs={
            "search_incidents": SearchIncidentsInput(
                query="VPN"
            )
        },
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.state.tool_calls == [
        "search_incidents"
    ]
    assert result.output == (
        "1 incidente(s) encontrado(s)."
    )


def test_orchestrator_appends_note_to_known_incident(
    operational_tools,
):
    incident = operational_tools["create"].run(
        _incident_input()
    )

    orchestrator = AdaptiveOrchestrator(
        planner=RuleBasedPlanner(),
        knowledge_tool=StubKnowledgeTool(),
        create_incident_tool=operational_tools["create"],
        search_incidents_tool=operational_tools["search"],
        append_incident_note_tool=operational_tools["append"],
    )

    result = orchestrator.execute(
        _state(
            "Agrega una nota de seguimiento "
            f"al incidente {incident.public_id}."
        ),
        tool_inputs={
            "append_incident_note": (
                AppendIncidentNoteInput(
                    incident_id=incident.public_id,
                    note="Identidad del usuario validada.",
                )
            )
        },
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.state.tool_calls == [
        "search_incidents",
        "append_incident_note",
    ]

    notes = operational_tools[
        "repository"
    ].list_notes(incident.public_id)

    assert len(notes) == 1
    assert notes[0].note == (
        "Identidad del usuario validada."
    )


def test_orchestrator_stops_when_incident_does_not_exist(
    operational_tools,
):
    orchestrator = AdaptiveOrchestrator(
        planner=RuleBasedPlanner(),
        knowledge_tool=StubKnowledgeTool(),
        create_incident_tool=operational_tools["create"],
        search_incidents_tool=operational_tools["search"],
        append_incident_note_tool=operational_tools["append"],
    )

    result = orchestrator.execute(
        _state(
            "Agrega una nota de seguimiento "
            "al incidente INC-99999."
        ),
        tool_inputs={
            "append_incident_note": (
                AppendIncidentNoteInput(
                    incident_id="INC-99999",
                    note="Seguimiento.",
                )
            )
        },
    )

    assert (
        result.status
        == ExecutionStatus.NEEDS_CLARIFICATION
    )
    assert result.state.tool_calls == [
        "search_incidents"
    ]


def test_orchestrator_requests_note_payload_when_missing(
    operational_tools,
):
    incident = operational_tools["create"].run(
        _incident_input()
    )

    orchestrator = AdaptiveOrchestrator(
        planner=RuleBasedPlanner(),
        knowledge_tool=StubKnowledgeTool(),
        create_incident_tool=operational_tools["create"],
        search_incidents_tool=operational_tools["search"],
        append_incident_note_tool=operational_tools["append"],
    )

    result = orchestrator.execute(
        _state(
            "Agrega una nota de seguimiento "
            f"al incidente {incident.public_id}."
        )
    )

    assert (
        result.status
        == ExecutionStatus.NEEDS_CLARIFICATION
    )
    assert result.state.tool_calls == [
        "search_incidents"
    ]
    assert result.state.requires_clarification is True


def test_orchestrator_clarifies_followup_without_memory_instead_of_querying_rag(
    operational_tools,
):
    knowledge = StubKnowledgeTool()

    orchestrator = AdaptiveOrchestrator(
        planner=RuleBasedPlanner(),
        knowledge_tool=knowledge,
        create_incident_tool=operational_tools["create"],
        search_incidents_tool=operational_tools["search"],
        append_incident_note_tool=operational_tools["append"],
    )

    result = orchestrator.execute(
        _state(
            "Agrega que la identidad ya fue validada."
        ),
        tool_inputs={
            "append_incident_note": AppendIncidentNoteDraft(
                note="Identidad del usuario validada."
            )
        },
    )

    assert (
        result.status
        == ExecutionStatus.NEEDS_CLARIFICATION
    )
    assert result.state.intent == "incident_note"
    assert result.state.tool_calls == []
    assert knowledge.calls == []
    assert result.output == (
        "¿A qué incidente deseas agregar el seguimiento?"
    )
