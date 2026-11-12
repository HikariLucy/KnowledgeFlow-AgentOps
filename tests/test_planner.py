"""Tests for deterministic KnowledgeFlow planning."""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.agentic.planner import (
    PlanningIntent,
    RuleBasedPlanner,
)
from app.agentic.state import AgentState
from app.memory.short_term import ShortTermMemory


def _state(request: str) -> AgentState:
    return AgentState(
        conversation_id="conv-1",
        user_request=request,
    )


def test_planner_routes_general_question_to_knowledge():
    planner = RuleBasedPlanner()

    state = _state(
        "¿Qué requisitos debe cumplir una contraseña?"
    )

    decision = planner.plan(state)

    assert decision.intent == PlanningIntent.KNOWLEDGE_QUERY
    assert decision.required_tools == [
        "search_knowledge"
    ]

    assert state.intent == "knowledge_query"
    assert state.plan == [
        "Consultar base de conocimiento"
    ]
    assert state.iteration_count == 1


def test_planner_creates_multi_step_incident_plan():
    planner = RuleBasedPlanner()

    state = _state(
        "Perdí mi autenticador. "
        "Revisa el procedimiento y registra un incidente."
    )

    decision = planner.plan(state)

    assert decision.intent == PlanningIntent.INCIDENT_CREATE
    assert decision.required_tools == [
        "search_knowledge",
        "create_incident",
    ]

    assert state.requires_clarification is False
    assert len(state.plan) == 3


def test_planner_routes_incident_search():
    planner = RuleBasedPlanner()

    state = _state(
        "Busca los incidentes relacionados con VPN."
    )

    decision = planner.plan(state)

    assert decision.intent == PlanningIntent.INCIDENT_SEARCH
    assert decision.required_tools == [
        "search_incidents"
    ]


def test_planner_routes_incident_note_with_explicit_id():
    planner = RuleBasedPlanner()

    state = _state(
        "Agrega una nota de seguimiento "
        "al incidente INC-00042."
    )

    decision = planner.plan(state)

    assert decision.intent == PlanningIntent.INCIDENT_NOTE
    assert decision.incident_id == "INC-00042"
    assert decision.required_tools == [
        "search_incidents",
        "append_incident_note",
    ]

    assert state.incident_id == "INC-00042"
    assert state.requires_clarification is False


def test_planner_requests_clarification_when_incident_id_is_missing():
    planner = RuleBasedPlanner()

    state = _state(
        "Agrega una nota de seguimiento al incidente."
    )

    decision = planner.plan(state)

    assert decision.intent == PlanningIntent.INCIDENT_NOTE
    assert decision.requires_clarification is True
    assert decision.required_tools == []

    assert state.requires_clarification is True
    assert state.clarification_question is not None


def test_planner_can_resolve_incident_from_existing_memory_context():
    planner = RuleBasedPlanner()

    state = _state(
        "Agrega una nota de seguimiento al incidente."
    )

    state.memory_context = [
        {
            "memory_kind": "long_term",
            "content": "Se creó el incidente INC-00017 por MFA.",
            "metadata": {},
        }
    ]

    decision = planner.plan(state)

    assert decision.requires_clarification is False
    assert decision.incident_id == "INC-00017"
    assert state.incident_id == "INC-00017"


def test_planner_loads_short_term_memory():
    short_term = ShortTermMemory()

    short_term.add_message(
        "conv-1",
        "user",
        "Antes tuvimos un problema de acceso.",
    )

    short_term.add_message(
        "conv-1",
        "assistant",
        "Revisamos el procedimiento correspondiente.",
    )

    planner = RuleBasedPlanner(
        short_term_memory=short_term
    )

    state = _state(
        "¿Qué recomienda la política?"
    )

    planner.plan(state)

    assert len(state.memory_context) == 2
    assert state.memory_context[0]["memory_kind"] == "short_term"
    assert state.memory_context[0]["role"] == "user"


def test_planner_loads_semantic_memory_and_reuses_incident_id():
    memory_record = SimpleNamespace(
        public_id="MEM-00001",
        memory_type=SimpleNamespace(value="tool_result"),
        content="Se creó el incidente INC-00031 por pérdida de MFA.",
        metadata={
            "incident_id": "INC-00031",
        },
    )

    semantic_result = SimpleNamespace(
        memory=memory_record,
        score=0.93,
    )

    semantic_memory = SimpleNamespace(
        search=lambda **kwargs: [semantic_result]
    )

    planner = RuleBasedPlanner(
        semantic_memory=semantic_memory
    )

    state = _state(
        "Agrega una nota de seguimiento al incidente."
    )

    decision = planner.plan(state)

    assert len(state.memory_context) == 1
    assert state.memory_context[0]["memory_kind"] == "long_term"

    assert decision.incident_id == "INC-00031"
    assert decision.requires_clarification is False
    assert state.incident_id == "INC-00031"


def test_planner_uses_incident_memory_for_natural_follow_up():
    planner = RuleBasedPlanner()

    state = _state(
        "Agrega que la identidad ya fue validada."
    )

    state.memory_context = [
        {
            "memory_kind": "long_term",
            "content": "Se creó el incidente INC-00017 por pérdida de MFA.",
            "metadata": {
                "incident_id": "INC-00017",
            },
        }
    ]

    decision = planner.plan(state)

    assert decision.intent == PlanningIntent.INCIDENT_NOTE
    assert decision.incident_id == "INC-00017"
    assert decision.required_tools == [
        "search_incidents",
        "append_incident_note",
    ]
    assert decision.requires_clarification is False


def test_planner_prefers_most_recent_short_term_incident():
    planner = RuleBasedPlanner()

    state = _state(
        "Agrega que la identidad ya fue validada."
    )

    state.memory_context = [
        {
            "memory_kind": "short_term",
            "role": "assistant",
            "content": "Incidente creado: INC-00001.",
        },
        {
            "memory_kind": "short_term",
            "role": "assistant",
            "content": "Incidente creado: INC-00002.",
        },
    ]

    decision = planner.plan(state)

    assert decision.intent == PlanningIntent.INCIDENT_NOTE
    assert decision.incident_id == "INC-00002"


def test_planner_prefers_newest_long_term_incident_over_higher_similarity():
    older_memory = SimpleNamespace(
        public_id="MEM-00001",
        memory_type=SimpleNamespace(value="tool_result"),
        content="Se creó el incidente INC-00001 por pérdida de MFA.",
        metadata={"incident_id": "INC-00001"},
        created_at=datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc),
    )
    newer_memory = SimpleNamespace(
        public_id="MEM-00002",
        memory_type=SimpleNamespace(value="tool_result"),
        content="Se creó el incidente INC-00002 por pérdida de MFA.",
        metadata={"incident_id": "INC-00002"},
        created_at=datetime(2026, 9, 29, 10, 5, tzinfo=timezone.utc),
    )

    semantic_memory = SimpleNamespace(
        search=lambda **kwargs: [
            SimpleNamespace(
                memory=older_memory,
                score=0.95,
            ),
            SimpleNamespace(
                memory=newer_memory,
                score=0.70,
            ),
        ]
    )

    planner = RuleBasedPlanner(
        semantic_memory=semantic_memory
    )

    decision = planner.plan(
        _state(
            "Agrega que la identidad ya fue validada."
        )
    )

    assert decision.intent == PlanningIntent.INCIDENT_NOTE
    assert decision.incident_id == "INC-00002"


def test_planner_uses_append_payload_as_incident_note_hint_without_memory():
    planner = RuleBasedPlanner()

    state = _state(
        "Agrega que la identidad ya fue validada."
    )

    decision = planner.plan(
        state,
        requested_tools={"append_incident_note"},
    )

    assert decision.intent == PlanningIntent.INCIDENT_NOTE
    assert decision.requires_clarification is True
    assert decision.required_tools == []
    assert decision.clarification_question == (
        "¿A qué incidente deseas agregar el seguimiento?"
    )
