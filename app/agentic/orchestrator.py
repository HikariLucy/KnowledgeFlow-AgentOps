"""Adaptive execution orchestrator for KnowledgeFlow Agent."""

from enum import Enum

from pydantic import BaseModel

from app.agentic.planner import RuleBasedPlanner
from app.agentic.state import AgentState
from app.memory.write_back import MemoryWriteBack
from app.tools.incidents import (
    AppendIncidentNoteTool,
    CreateIncidentTool,
    SearchIncidentsTool,
)
from app.tools.knowledge import KnowledgeRAGTool
from app.tools.schemas import (
    AppendIncidentNoteDraft,
    AppendIncidentNoteInput,
    CreateIncidentInput,
    KnowledgeQueryInput,
    SearchIncidentsInput,
)


class ExecutionStatus(str, Enum):
    """Controlled outcomes of an agentic execution."""

    COMPLETED = "completed"
    NEEDS_CLARIFICATION = "needs_clarification"
    ABSTAINED = "abstained"
    FAILED = "failed"


class OrchestrationResult(BaseModel):
    """Structured result exposed by the orchestration layer."""

    status: ExecutionStatus
    state: AgentState
    output: str | None = None


class AdaptiveOrchestrator:
    """Execute planner decisions while enforcing safe adaptive stops.

    The orchestrator does not generate tool arguments from unconstrained
    natural language. Write operations require already validated Pydantic
    inputs. This boundary will later be populated by specialized agents.
    """

    def __init__(
        self,
        planner: RuleBasedPlanner,
        knowledge_tool: KnowledgeRAGTool | None = None,
        create_incident_tool: CreateIncidentTool | None = None,
        search_incidents_tool: SearchIncidentsTool | None = None,
        append_incident_note_tool: AppendIncidentNoteTool | None = None,
        memory_write_back: MemoryWriteBack | None = None,
    ) -> None:
        self.planner = planner
        self.knowledge_tool = knowledge_tool
        self.create_incident_tool = create_incident_tool
        self.search_incidents_tool = search_incidents_tool
        self.append_incident_note_tool = append_incident_note_tool
        self.memory_write_back = memory_write_back

    @staticmethod
    def _tool_input(
        tool_inputs: dict[str, object],
        name: str,
        expected_type: type,
    ):
        """Return one tool input only when it matches the expected schema."""
        value = tool_inputs.get(name)

        if isinstance(value, expected_type):
            return value

        return None

    def _finalize(
        self,
        result: OrchestrationResult,
    ) -> OrchestrationResult:
        """Persist conversational and operational memory without breaking execution."""
        if self.memory_write_back is None:
            return result

        try:
            self.memory_write_back.record(
                state=result.state,
                output=result.output,
                status=result.status.value,
            )
        except Exception as exc:
            result.state.observations.append(
                {
                    "component": "memory_write_back",
                    "status": "unavailable",
                    "error_type": type(exc).__name__,
                }
            )

        return result

    def _clarification(
        self,
        state: AgentState,
        question: str,
    ) -> OrchestrationResult:
        """Stop execution and request missing information."""
        state.requires_clarification = True
        state.clarification_question = question

        return self._finalize(
            OrchestrationResult(
                status=ExecutionStatus.NEEDS_CLARIFICATION,
                state=state,
                output=question,
            )
        )

    def _failure(
        self,
        state: AgentState,
        component: str,
    ) -> OrchestrationResult:
        """Return a controlled failure for a missing runtime component."""
        state.observations.append(
            {
                "component": component,
                "status": "unavailable",
            }
        )

        return self._finalize(
            OrchestrationResult(
                status=ExecutionStatus.FAILED,
                state=state,
                output=f"Componente no disponible: {component}.",
            )
        )

    def execute(
        self,
        state: AgentState,
        tool_inputs: dict[str, object] | None = None,
    ) -> OrchestrationResult:
        """Plan and execute tools sequentially with adaptive safety checks."""
        inputs = tool_inputs or {}

        decision = self.planner.plan(
            state,
            requested_tools=set(inputs),
        )

        if decision.requires_clarification:
            return self._clarification(
                state,
                decision.clarification_question
                or "Se requiere información adicional.",
            )

        output: str | None = None

        for tool_name in decision.required_tools:
            if tool_name == "search_knowledge":
                if self.knowledge_tool is None:
                    return self._failure(
                        state,
                        "search_knowledge",
                    )

                arguments = self._tool_input(
                    inputs,
                    "search_knowledge",
                    KnowledgeQueryInput,
                )

                if arguments is None:
                    arguments = KnowledgeQueryInput(
                        query=state.user_request,
                    )

                state.register_tool_call(
                    "search_knowledge"
                )

                result = self.knowledge_tool.run(
                    arguments
                )

                state.retrieved_context = [
                    source.model_dump()
                    for source in result.sources
                ]

                state.observations.append(
                    {
                        "tool": "search_knowledge",
                        "status": "abstained"
                        if result.abstained
                        else "completed",
                        "source_scope": result.source_scope,
                        "citations": list(result.citations),
                        "source_count": len(result.sources),
                    }
                )

                output = result.answer

                if (
                    "Consultar conocimiento aplicable"
                    in state.plan
                ):
                    state.mark_step_completed(
                        "Consultar conocimiento aplicable"
                    )
                else:
                    state.mark_step_completed(
                        "Consultar base de conocimiento"
                    )

                if result.abstained:
                    return self._finalize(
                        OrchestrationResult(
                            status=ExecutionStatus.ABSTAINED,
                            state=state,
                            output=result.answer,
                        )
                    )

            elif tool_name == "create_incident":
                if self.create_incident_tool is None:
                    return self._failure(
                        state,
                        "create_incident",
                    )

                arguments = self._tool_input(
                    inputs,
                    "create_incident",
                    CreateIncidentInput,
                )

                if arguments is None:
                    return self._clarification(
                        state,
                        (
                            "Para registrar el incidente necesito "
                            "título, descripción, categoría y severidad "
                            "validados."
                        ),
                    )

                state.mark_step_completed(
                    "Validar información mínima del incidente"
                )

                state.register_tool_call(
                    "create_incident"
                )

                incident = self.create_incident_tool.run(
                    arguments
                )

                state.incident_id = incident.public_id

                state.observations.append(
                    {
                        "tool": "create_incident",
                        "status": "completed",
                        "incident_id": incident.public_id,
                    }
                )

                state.mark_step_completed(
                    "Crear incidente"
                )

                incident_message = (
                    f"Incidente creado: "
                    f"{incident.public_id}."
                )

                if output:
                    output = (
                        f"{output}\n\n"
                        f"{incident_message}"
                    )
                else:
                    output = incident_message

            elif tool_name == "search_incidents":
                if self.search_incidents_tool is None:
                    return self._failure(
                        state,
                        "search_incidents",
                    )

                arguments = self._tool_input(
                    inputs,
                    "search_incidents",
                    SearchIncidentsInput,
                )

                if arguments is None:
                    if state.incident_id:
                        arguments = SearchIncidentsInput(
                            query=state.incident_id,
                        )
                    else:
                        arguments = SearchIncidentsInput(
                            query=state.user_request,
                        )

                state.register_tool_call(
                    "search_incidents"
                )

                incidents = self.search_incidents_tool.run(
                    arguments
                )

                state.observations.append(
                    {
                        "tool": "search_incidents",
                        "status": "completed",
                        "result_count": len(incidents),
                        "incident_ids": [
                            incident.public_id
                            for incident in incidents
                        ],
                    }
                )

                if (
                    "Buscar incidentes relacionados"
                    in state.plan
                ):
                    state.mark_step_completed(
                        "Buscar incidentes relacionados"
                    )

                if "Localizar incidente" in state.plan:
                    if not incidents:
                        return self._clarification(
                            state,
                            (
                                "No encontré el incidente indicado. "
                                "¿Puedes confirmar su identificador?"
                            ),
                        )

                    state.mark_step_completed(
                        "Localizar incidente"
                    )

                output = (
                    f"{len(incidents)} "
                    "incidente(s) encontrado(s)."
                )

            elif tool_name == "append_incident_note":
                if self.append_incident_note_tool is None:
                    return self._failure(
                        state,
                        "append_incident_note",
                    )

                arguments = self._tool_input(
                    inputs,
                    "append_incident_note",
                    AppendIncidentNoteInput,
                )

                if arguments is None:
                    draft = self._tool_input(
                        inputs,
                        "append_incident_note",
                        AppendIncidentNoteDraft,
                    )

                    if draft is None:
                        return self._clarification(
                            state,
                            (
                                "¿Qué información de seguimiento "
                                "deseas agregar al incidente?"
                            ),
                        )

                    incident_id = draft.incident_id or state.incident_id

                    if incident_id is None:
                        return self._clarification(
                            state,
                            (
                                "¿A qué incidente deseas agregar "
                                "el seguimiento?"
                            ),
                        )

                    arguments = AppendIncidentNoteInput(
                        incident_id=incident_id,
                        note=draft.note,
                    )

                if (
                    state.incident_id
                    and arguments.incident_id
                    != state.incident_id
                ):
                    return self._clarification(
                        state,
                        (
                            "El identificador del seguimiento "
                            "no coincide con el incidente "
                            "seleccionado."
                        ),
                    )

                state.register_tool_call(
                    "append_incident_note"
                )

                note = self.append_incident_note_tool.run(
                    arguments
                )

                state.observations.append(
                    {
                        "tool": "append_incident_note",
                        "status": "completed",
                        "incident_id": (
                            note.incident_public_id
                        ),
                    }
                )

                state.mark_step_completed(
                    "Agregar nota de seguimiento"
                )

                output = (
                    "Seguimiento agregado a "
                    f"{note.incident_public_id}."
                )

            else:
                return self._failure(
                    state,
                    tool_name,
                )

        return self._finalize(
            OrchestrationResult(
                status=ExecutionStatus.COMPLETED,
                state=state,
                output=output,
            )
        )
