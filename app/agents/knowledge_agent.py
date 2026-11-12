"""Knowledge specialist agent."""

from app.agents.profile import AgentProfile
from app.tools.knowledge import KnowledgeRAGTool
from app.tools.schemas import (
    KnowledgeQueryInput,
    KnowledgeQueryResult,
)


KNOWLEDGE_AGENT_PROFILE = AgentProfile(
    name="knowledge_agent",
    role="Knowledge Agent",
    goal=(
        "Recuperar evidencia documental relevante y entregar "
        "respuestas fundamentadas y trazables."
    ),
    backstory=(
        "Especialista en conocimiento organizacional. Consulta exclusivamente "
        "el pipeline RAG y no realiza escrituras operacionales."
    ),
    allow_delegation=False,
    tools=("search_knowledge",),
)


class KnowledgeAgent:
    """Specialist restricted to organizational knowledge retrieval."""

    profile = KNOWLEDGE_AGENT_PROFILE

    def __init__(
        self,
        knowledge_tool: KnowledgeRAGTool,
    ) -> None:
        self.knowledge_tool = knowledge_tool

    def query(
        self,
        arguments: KnowledgeQueryInput,
    ) -> KnowledgeQueryResult:
        """Execute the knowledge retrieval capability."""
        return self.knowledge_tool.run(arguments)
