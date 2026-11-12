"""Application service exposing the deterministic agentic workflow."""

from app.agentic.orchestrator import AdaptiveOrchestrator
from app.agentic.state import AgentState
from app.api.agent_schemas import AgentRequest, AgentResponse


class AgentService:
    """Execute one validated API turn through the KnowledgeFlow orchestrator."""

    def __init__(self, orchestrator: AdaptiveOrchestrator) -> None:
        self.orchestrator = orchestrator

    def execute(self, request: AgentRequest) -> AgentResponse:
        """Run one turn and return a traceable response without private reasoning."""
        state = AgentState(
            conversation_id=request.conversation_id,
            user_request=request.message,
        )

        tool_inputs: dict[str, object] = {}

        if request.knowledge_query is not None:
            tool_inputs["search_knowledge"] = request.knowledge_query

        if request.create_incident is not None:
            tool_inputs["create_incident"] = request.create_incident

        if request.search_incidents is not None:
            tool_inputs["search_incidents"] = request.search_incidents

        if request.append_incident_note is not None:
            tool_inputs["append_incident_note"] = request.append_incident_note

        result = self.orchestrator.execute(
            state,
            tool_inputs=tool_inputs,
        )

        return AgentResponse(
            status=result.status,
            conversation_id=result.state.conversation_id,
            intent=result.state.intent,
            plan=list(result.state.plan),
            required_tools=list(result.state.required_tools),
            tool_calls=list(result.state.tool_calls),
            completed_steps=list(result.state.completed_steps),
            memory_context=list(result.state.memory_context),
            sources=list(result.state.retrieved_context),
            observations=list(result.state.observations),
            incident_id=result.state.incident_id,
            requires_clarification=result.state.requires_clarification,
            clarification_question=result.state.clarification_question,
            iteration_count=result.state.iteration_count,
            output=result.output,
        )
