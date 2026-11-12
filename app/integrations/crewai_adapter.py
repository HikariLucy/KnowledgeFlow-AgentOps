"""CrewAI integration layer for KnowledgeFlow Agent."""

from crewai import Agent, Crew, LLM, Process, Task

from app.agents.knowledge_agent import KNOWLEDGE_AGENT_PROFILE
from app.agents.manager import MANAGER_PROFILE
from app.agents.operations_agent import OPERATIONS_AGENT_PROFILE
from app.core.config import Settings, get_settings
from app.integrations.crewai_tools import (
    CrewAIAppendIncidentNoteTool,
    CrewAICreateIncidentTool,
    CrewAIKnowledgeTool,
    CrewAISearchIncidentsTool,
)
from app.tools.incidents import (
    AppendIncidentNoteTool,
    CreateIncidentTool,
    SearchIncidentsTool,
)
from app.tools.knowledge import KnowledgeRAGTool


class CrewAIAdapter:
    """Build a CrewAI hierarchy from validated KnowledgeFlow components."""

    def __init__(
        self,
        knowledge_tool: KnowledgeRAGTool,
        create_incident_tool: CreateIncidentTool,
        search_incidents_tool: SearchIncidentsTool,
        append_incident_note_tool: AppendIncidentNoteTool,
        *,
        settings: Settings | None = None,
        llm: LLM | None = None,
    ) -> None:
        self.settings = settings or get_settings()

        self.llm = llm or self._build_llm()

        self.knowledge_tool = CrewAIKnowledgeTool(
            knowledge_tool
        )

        self.create_incident_tool = (
            CrewAICreateIncidentTool(
                create_incident_tool
            )
        )

        self.search_incidents_tool = (
            CrewAISearchIncidentsTool(
                search_incidents_tool
            )
        )

        self.append_incident_note_tool = (
            CrewAIAppendIncidentNoteTool(
                append_incident_note_tool
            )
        )

    def _build_llm(self) -> LLM:
        """Create the native Gemini model used by CrewAI."""
        api_key = self.settings.gemini_api_key

        if not api_key or not api_key.strip():
            raise RuntimeError(
                "GEMINI_API_KEY is required to build the CrewAI LLM."
            )

        return LLM(
            model=f"gemini/{self.settings.gemini_chat_model}",
            api_key=api_key,
            temperature=self.settings.llm_temperature,
        )

    def build_manager(self) -> Agent:
        """Create the manager without operational tools."""
        return Agent(
            role=MANAGER_PROFILE.role,
            goal=MANAGER_PROFILE.goal,
            backstory=MANAGER_PROFILE.backstory,
            allow_delegation=True,
            tools=[],
            llm=self.llm,
            max_iter=6,
            verbose=False,
        )

    def build_knowledge_agent(self) -> Agent:
        """Create the RAG specialist."""
        return Agent(
            role=KNOWLEDGE_AGENT_PROFILE.role,
            goal=KNOWLEDGE_AGENT_PROFILE.goal,
            backstory=KNOWLEDGE_AGENT_PROFILE.backstory,
            allow_delegation=False,
            tools=[
                self.knowledge_tool,
            ],
            llm=self.llm,
            max_iter=6,
            verbose=False,
        )

    def build_operations_agent(self) -> Agent:
        """Create the operational specialist."""
        return Agent(
            role=OPERATIONS_AGENT_PROFILE.role,
            goal=OPERATIONS_AGENT_PROFILE.goal,
            backstory=OPERATIONS_AGENT_PROFILE.backstory,
            allow_delegation=False,
            tools=[
                self.create_incident_tool,
                self.search_incidents_tool,
                self.append_incident_note_tool,
            ],
            llm=self.llm,
            max_iter=6,
            verbose=False,
        )

    def build_task(self) -> Task:
        """Create the manager-led organizational task."""
        return Task(
            description=(
                "Atender la solicitud organizacional recibida en "
                "{user_request}. Delegar únicamente a especialistas "
                "con las capacidades necesarias. Las operaciones de "
                "escritura deben usar argumentos validados y no deben "
                "ejecutarse cuando la evidencia sea insuficiente."
            ),
            expected_output=(
                "Una respuesta final clara y trazable que indique "
                "el resultado de la solicitud, la evidencia relevante "
                "y cualquier acción operacional ejecutada."
            ),
        )

    def build_crew(self) -> Crew:
        """Create the hierarchical CrewAI crew without executing it."""
        manager = self.build_manager()
        knowledge = self.build_knowledge_agent()
        operations = self.build_operations_agent()

        return Crew(
            agents=[
                knowledge,
                operations,
            ],
            tasks=[
                self.build_task(),
            ],
            manager_agent=manager,
            process=Process.hierarchical,
            cache=False,
            memory=False,
            planning=False,
            verbose=False,
        )
