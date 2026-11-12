"""Offline tests for POST /api/agent and AgentService mapping."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.agentic.orchestrator import ExecutionStatus, OrchestrationResult
from app.agentic.service import AgentService
from app.agentic.state import AgentState
from app.api.agent_routes import get_agent_service
from app.api.agent_schemas import AgentRequest, AgentResponse
from app.main import app


class FakeAgentService:
    """Deterministic HTTP-layer service double."""

    def __init__(self) -> None:
        self.requests = []

    def execute(self, request: AgentRequest) -> AgentResponse:
        self.requests.append(request)

        return AgentResponse(
            status=ExecutionStatus.COMPLETED,
            conversation_id=request.conversation_id,
            intent="knowledge_query",
            plan=["Consultar base de conocimiento"],
            required_tools=["search_knowledge"],
            tool_calls=["search_knowledge"],
            completed_steps=["Consultar base de conocimiento"],
            sources=[
                {
                    "id": "S1",
                    "file_name": "faq_interna.txt",
                    "source_type": "internal",
                    "chunk_index": 1,
                    "score": 0.91,
                }
            ],
            observations=[
                {
                    "tool": "search_knowledge",
                    "status": "completed",
                }
            ],
            iteration_count=1,
            output="Respuesta grounded [S1].",
        )


def test_agent_api_returns_structured_trace():
    service = FakeAgentService()
    app.dependency_overrides[get_agent_service] = lambda: service

    client = TestClient(app)

    try:
        response = client.post(
            "/api/agent",
            json={
                "conversation_id": "demo-001",
                "message": "¿Qué hago si pierdo mi MFA?",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "completed"
    assert data["conversation_id"] == "demo-001"
    assert data["intent"] == "knowledge_query"
    assert data["tool_calls"] == ["search_knowledge"]
    assert data["sources"][0]["file_name"] == "faq_interna.txt"
    assert data["output"] == "Respuesta grounded [S1]."


def test_agent_api_rejects_blank_message():
    app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/agent",
            json={
                "conversation_id": "demo-001",
                "message": "   ",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_agent_api_parses_typed_incident_payload():
    service = FakeAgentService()
    app.dependency_overrides[get_agent_service] = lambda: service

    client = TestClient(app)

    try:
        response = client.post(
            "/api/agent",
            json={
                "conversation_id": "demo-002",
                "message": (
                    "Revisa el procedimiento y registra un incidente."
                ),
                "create_incident": {
                    "title": "Pérdida de autenticador MFA",
                    "description": "Usuario perdió el dispositivo MFA.",
                    "category": "access",
                    "severity": "medium",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(service.requests) == 1

    parsed = service.requests[0].create_incident

    assert parsed is not None
    assert parsed.title == "Pérdida de autenticador MFA"
    assert parsed.category.value == "access"
    assert parsed.severity.value == "medium"


def test_agent_service_maps_orchestration_state_to_response():
    state = AgentState(
        conversation_id="conv-service",
        user_request="Busca conocimiento.",
    )
    state.intent = "knowledge_query"
    state.plan = ["Consultar base de conocimiento"]
    state.required_tools = ["search_knowledge"]
    state.tool_calls = ["search_knowledge"]
    state.completed_steps = ["Consultar base de conocimiento"]
    state.retrieved_context = [
        {
            "id": "S1",
            "file_name": "faq_interna.txt",
            "source_type": "internal",
            "chunk_index": 1,
            "score": 0.9,
        }
    ]
    state.memory_context = [
        {
            "memory_kind": "short_term",
            "role": "user",
            "content": "Contexto previo.",
        }
    ]
    state.observations = [
        {
            "tool": "search_knowledge",
            "status": "completed",
        }
    ]
    state.iteration_count = 1

    orchestration_result = OrchestrationResult(
        status=ExecutionStatus.COMPLETED,
        state=state,
        output="Respuesta [S1].",
    )

    fake_orchestrator = SimpleNamespace(
        execute=lambda *_args, **_kwargs: orchestration_result
    )

    service = AgentService(fake_orchestrator)

    response = service.execute(
        AgentRequest(
            conversation_id="conv-service",
            message="Busca conocimiento.",
        )
    )

    assert response.status == ExecutionStatus.COMPLETED
    assert response.conversation_id == "conv-service"
    assert response.intent == "knowledge_query"
    assert response.required_tools == ["search_knowledge"]
    assert response.tool_calls == ["search_knowledge"]
    assert response.memory_context[0]["content"] == "Contexto previo."
    assert response.sources[0]["file_name"] == "faq_interna.txt"
    assert response.output == "Respuesta [S1]."


def test_agent_api_accepts_followup_without_incident_id():
    service = FakeAgentService()
    app.dependency_overrides[get_agent_service] = lambda: service

    client = TestClient(app)

    try:
        response = client.post(
            "/api/agent",
            json={
                "conversation_id": "demo-memory",
                "message": "Agrega que la identidad ya fue validada.",
                "append_incident_note": {
                    "note": "Identidad del usuario validada."
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(service.requests) == 1

    draft = service.requests[0].append_incident_note

    assert draft is not None
    assert draft.incident_id is None
    assert draft.note == "Identidad del usuario validada."


def test_agent_ui_route_serves_workspace():
    client = TestClient(app)

    response = client.get("/agent")

    assert response.status_code == 200
    assert "KnowledgeFlow Agent" in response.text
    assert "agent.js" in response.text


def test_agent_ui_exposes_guided_memory_followup_action():
    client = TestClient(app)

    response = client.get("/agent")

    assert response.status_code == 200
    assert "prepare-followup-btn" in response.text
    assert "Continuar con seguimiento" in response.text
    assert "Cargar creación MFA" in response.text
