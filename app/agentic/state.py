"""Shared execution state for KnowledgeFlow Agent."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class AgentState(BaseModel):
    """State shared across the agentic workflow.

    This object represents the operational state of one execution:
    request, plan, observations, completed steps and safety limits.
    It is intentionally separate from conversational long-term memory.
    """

    conversation_id: str
    user_request: str

    intent: str | None = None
    plan: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)

    retrieved_context: list[dict[str, Any]] = Field(default_factory=list)
    memory_context: list[dict[str, Any]] = Field(default_factory=list)

    selected_tool: str | None = None
    tool_calls: list[str] = Field(default_factory=list)
    observations: list[dict[str, Any]] = Field(default_factory=list)

    incident_id: str | None = None

    completed_steps: list[str] = Field(default_factory=list)
    requires_clarification: bool = False
    clarification_question: str | None = None

    iteration_count: int = Field(default=0, ge=0)
    max_iterations: int = Field(default=6, ge=1)

    @field_validator("conversation_id", "user_request")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        """Reject empty or whitespace-only identifiers and requests."""
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty or whitespace only")
        return value

    @property
    def can_continue(self) -> bool:
        """Return whether another reasoning/execution iteration is allowed."""
        return self.iteration_count < self.max_iterations

    def register_iteration(self) -> None:
        """Register one reasoning iteration while enforcing the safety limit."""
        if not self.can_continue:
            raise RuntimeError(
                f"Maximum number of iterations reached: {self.max_iterations}"
            )
        self.iteration_count += 1

    def mark_step_completed(self, step: str) -> None:
        """Record a completed plan step without duplicating it."""
        step = step.strip()
        if step and step not in self.completed_steps:
            self.completed_steps.append(step)

    def register_tool_call(self, tool_name: str) -> None:
        """Record a tool invocation for traceability."""
        tool_name = tool_name.strip()
        if tool_name:
            self.selected_tool = tool_name
            self.tool_calls.append(tool_name)
