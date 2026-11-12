"""Tests for KnowledgeFlow specialist-agent boundaries."""

import pytest

from app.agentic.planner import (
    PlanningIntent,
    RuleBasedPlanner,
)
from app.agentic.state import AgentState
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.manager import ManagerAgent
from app.agents.operations_agent import OperationsAgent
from app.storage.database import SQLiteDatabase
from app.storage.repositories import IncidentRepository
from app.tools.incidents import (
    AppendIncidentNoteTool,
    CreateIncidentTool,
    SearchIncidentsTool,
)
from app.tools.schemas import (
    AppendIncidentNoteInput,
    CreateIncidentInput,
    KnowledgeQueryResult,
    KnowledgeSource,
    SearchIncidentsInput,
)


class StubKnowledgeTool:
    """Deterministic RAG-tool double."""

    def run(self, arguments):
        return KnowledgeQueryResult(
            query=arguments.query,
            source_scope="internal",
            answer="Respuesta fundamentada [S1].",
            citations=["S1"],
            sources=[
                KnowledgeSource(
                    id="S1",
                    file_name="politica.md",
                    source_type="internal",
                    chunk_index=0,
                    score=0.91,
                )
            ],
            abstained=False,
        )


@pytest.fixture
def operations_agent(tmp_path):
    database = SQLiteDatabase(
        tmp_path / "agent-roles.db"
    )
    database.initialize()

    repository = IncidentRepository(database)

    return OperationsAgent(
        create_incident_tool=CreateIncidentTool(
            repository
        ),
        search_incidents_tool=SearchIncidentsTool(
            repository
        ),
        append_incident_note_tool=(
            AppendIncidentNoteTool(repository)
        ),
    )


def test_manager_has_no_tools_and_can_delegate():
    manager = ManagerAgent(
        planner=RuleBasedPlanner()
    )

    assert manager.profile.tools == ()
    assert manager.profile.allow_delegation is True


def test_manager_only_returns_plan():
    manager = ManagerAgent(
        planner=RuleBasedPlanner()
    )

    state = AgentState(
        conversation_id="conv-1",
        user_request=(
            "Busca los incidentes relacionados con VPN."
        ),
    )

    decision = manager.plan(state)

    assert (
        decision.intent
        == PlanningIntent.INCIDENT_SEARCH
    )
    assert decision.required_tools == [
        "search_incidents"
    ]
    assert state.tool_calls == []


def test_knowledge_agent_only_exposes_knowledge_tool():
    agent = KnowledgeAgent(
        knowledge_tool=StubKnowledgeTool()
    )

    assert agent.profile.tools == (
        "search_knowledge",
    )
    assert agent.profile.allow_delegation is False


def test_operations_agent_has_only_incident_tools(
    operations_agent,
):
    assert operations_agent.profile.tools == (
        "create_incident",
        "search_incidents",
        "append_incident_note",
    )

    assert (
        operations_agent.profile.allow_delegation
        is False
    )


def test_operations_agent_can_create_and_search_incident(
    operations_agent,
):
    incident = operations_agent.create_incident(
        CreateIncidentInput(
            title="Problema MFA",
            description="Pérdida de autenticador.",
            category="access",
            severity="medium",
        )
    )

    results = operations_agent.search_incidents(
        SearchIncidentsInput(
            query=incident.public_id
        )
    )

    assert len(results) == 1
    assert results[0].public_id == incident.public_id


def test_operations_agent_can_append_note(
    operations_agent,
):
    incident = operations_agent.create_incident(
        CreateIncidentInput(
            title="Problema VPN",
            description="Sin acceso a VPN.",
            category="access",
            severity="medium",
        )
    )

    note = operations_agent.append_incident_note(
        AppendIncidentNoteInput(
            incident_id=incident.public_id,
            note="Usuario contactado.",
        )
    )

    assert (
        note.incident_public_id
        == incident.public_id
    )
    assert note.note == "Usuario contactado."
