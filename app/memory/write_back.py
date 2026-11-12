"""Controlled memory write-back for completed agentic executions."""

from app.agentic.state import AgentState
from app.memory.models import (
    MemoryCreate,
    MemoryRole,
    MemoryType,
    MemoryRecord,
)
from app.memory.semantic import SemanticMemory
from app.memory.short_term import ShortTermMemory


class MemoryWriteBack:
    """Persist conversational context and selected operational events.

    Short-term memory records the user request and visible assistant output.
    Long-term semantic memory intentionally stores only operational events that
    are useful in later turns, avoiding indiscriminate persistence of every
    message or tool result.
    """

    def __init__(
        self,
        short_term_memory: ShortTermMemory | None = None,
        semantic_memory: SemanticMemory | None = None,
    ) -> None:
        self.short_term_memory = short_term_memory
        self.semantic_memory = semantic_memory

    def record(
        self,
        state: AgentState,
        output: str | None,
        status: str,
    ) -> list[MemoryRecord]:
        """Write one execution back to configured memory stores."""
        if self.short_term_memory is not None:
            self.short_term_memory.add_message(
                state.conversation_id,
                MemoryRole.USER,
                state.user_request,
            )

            if output and output.strip():
                self.short_term_memory.add_message(
                    state.conversation_id,
                    MemoryRole.ASSISTANT,
                    output,
                )

        persisted: list[MemoryRecord] = []

        if self.semantic_memory is None:
            return persisted

        for observation in state.observations:
            if observation.get("status") != "completed":
                continue

            tool = observation.get("tool")

            if tool not in {
                "create_incident",
                "append_incident_note",
            }:
                continue

            incident_id = (
                observation.get("incident_id")
                or state.incident_id
            )

            if not incident_id:
                continue

            if tool == "create_incident":
                content = (
                    f"Se creó el incidente {incident_id} "
                    "como resultado de la solicitud del usuario."
                )
            else:
                content = (
                    f"Se agregó seguimiento al incidente "
                    f"{incident_id}."
                )

            persisted.append(
                self.semantic_memory.remember(
                    MemoryCreate(
                        conversation_id=state.conversation_id,
                        content=content,
                        memory_type=MemoryType.TOOL_RESULT,
                        metadata={
                            "incident_id": incident_id,
                            "tool": tool,
                            "execution_status": status,
                            "intent": state.intent,
                        },
                    )
                )
            )

        return persisted
