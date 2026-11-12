"""Agent role profiles for KnowledgeFlow Agent."""

from pydantic import BaseModel, ConfigDict, Field


class AgentProfile(BaseModel):
    """Framework-independent description of one agent role."""

    model_config = ConfigDict(frozen=True)

    name: str
    role: str
    goal: str
    backstory: str

    allow_delegation: bool = False
    tools: tuple[str, ...] = Field(default_factory=tuple)
