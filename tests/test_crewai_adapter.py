"""Offline tests for the CrewAI integration layer."""

import json

import pytest
from crewai import LLM, Process

from app.integrations.crewai_adapter import CrewAIAdapter
from app.integrations.crewai_tools import (
    CrewAIKnowledgeTool,
)
from app.storage.database import SQLiteDatabase
from app.storage.repositories import IncidentRepository
from app.tools.incidents import (
    AppendIncidentNoteTool,
    CreateIncidentTool,
    SearchIncidentsTool,
)
from app.tools.schemas import (
    CreateIncidentInput,
    KnowledgeQueryResult,
    KnowledgeSource,
)


class StubKnowledgeTool:
    """Offline KnowledgeRAGTool-compatible double."""

    description = "Stub knowledge search."

    def run(self, arguments):
        return KnowledgeQueryResult(
            query=arguments.query,
            source_scope="internal",
            answer="Procedimiento encontrado [S1].",
            citations=["S1"],
            sources=[
                KnowledgeSource(
                    id="S1",
                    file_name="policy.md",
                    source_type="internal",
                    chunk_index=0,
                    score=0.95,
                )
            ],
            abstained=False,
        )


@pytest.fixture
def adapter(tmp_path):
    database = SQLiteDatabase(
        tmp_path / "crewai-adapter.db"
    )
    database.initialize()

    repository = IncidentRepository(database)

    test_llm = LLM(
        model="gemini/gemini-3.5-flash",
        api_key="offline-test-key",
        temperature=0.0,
    )

    return CrewAIAdapter(
        knowledge_tool=StubKnowledgeTool(),
        create_incident_tool=CreateIncidentTool(
            repository
        ),
        search_incidents_tool=SearchIncidentsTool(
            repository
        ),
        append_incident_note_tool=(
            AppendIncidentNoteTool(repository)
        ),
        llm=test_llm,
    )


def test_crewai_knowledge_tool_preserves_structured_result():
    tool = CrewAIKnowledgeTool(
        StubKnowledgeTool()
    )

    payload = json.loads(
        tool._run(
            query="¿Cuál es el procedimiento?"
        )
    )

    assert payload["abstained"] is False
    assert payload["citations"] == ["S1"]
    assert payload["sources"][0]["id"] == "S1"


def test_crewai_manager_has_no_operational_tools(adapter):
    manager = adapter.build_manager()

    assert manager.allow_delegation is True
    assert manager.tools == []


def test_crewai_knowledge_agent_has_only_rag_tool(adapter):
    agent = adapter.build_knowledge_agent()

    assert agent.allow_delegation is False
    assert [tool.name for tool in agent.tools] == [
        "search_knowledge"
    ]


def test_crewai_operations_agent_has_only_incident_tools(
    adapter,
):
    agent = adapter.build_operations_agent()

    assert [tool.name for tool in agent.tools] == [
        "create_incident",
        "search_incidents",
        "append_incident_note",
    ]


def test_crewai_incident_tool_executes_existing_domain_logic(
    adapter,
):
    raw = adapter.create_incident_tool._run(
        title="Problema MFA",
        description="Usuario perdió autenticador.",
        category="access",
        severity="medium",
    )

    result = json.loads(raw)

    assert result["public_id"] == "INC-00001"
    assert result["status"] == "open"


def test_crewai_task_has_explicit_expected_output(adapter):
    task = adapter.build_task()

    assert task.description
    assert task.expected_output


def test_crewai_builds_hierarchical_crew(adapter):
    crew = adapter.build_crew()

    assert crew.process == Process.hierarchical
    assert crew.manager_agent is not None
    assert crew.manager_agent.tools == []
    assert len(crew.agents) == 2
    assert len(crew.tasks) == 1
