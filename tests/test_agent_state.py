"""Unit tests for shared agent execution state."""

import pytest
from pydantic import ValidationError

from app.agentic.state import AgentState


def test_agent_state_defaults_are_isolated():
    first = AgentState(
        conversation_id="conv-1",
        user_request="Necesito ayuda con MFA",
    )
    second = AgentState(
        conversation_id="conv-2",
        user_request="Tengo un problema de acceso",
    )

    first.plan.append("Consultar política")

    assert first.plan == ["Consultar política"]
    assert second.plan == []


def test_agent_state_rejects_blank_required_text():
    with pytest.raises(ValidationError):
        AgentState(
            conversation_id="   ",
            user_request="Consulta válida",
        )


def test_agent_state_tracks_steps_and_tools():
    state = AgentState(
        conversation_id="conv-1",
        user_request="Registrar incidente",
    )

    state.mark_step_completed("Identificar intención")
    state.mark_step_completed("Identificar intención")
    state.register_tool_call("create_incident")

    assert state.completed_steps == ["Identificar intención"]
    assert state.selected_tool == "create_incident"
    assert state.tool_calls == ["create_incident"]


def test_agent_state_enforces_iteration_limit():
    state = AgentState(
        conversation_id="conv-1",
        user_request="Resolver tarea",
        max_iterations=2,
    )

    state.register_iteration()
    state.register_iteration()

    assert state.iteration_count == 2
    assert state.can_continue is False

    with pytest.raises(RuntimeError):
        state.register_iteration()
