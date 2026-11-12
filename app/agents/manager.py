"""Manager Agent for planning and delegation."""

from app.agentic.planner import (
    PlanDecision,
    RuleBasedPlanner,
)
from app.agentic.state import AgentState
from app.agents.profile import AgentProfile


MANAGER_PROFILE = AgentProfile(
    name="knowledgeflow_manager",
    role="Manager Agent",
    goal=(
        "Analizar solicitudes organizacionales, construir un plan "
        "seguro y delegar cada capacidad al agente especialista adecuado."
    ),
    backstory=(
        "Coordinador de KnowledgeFlow Agent. No ejecuta herramientas "
        "operacionales directamente; planifica, delega y controla el flujo."
    ),
    allow_delegation=True,
    tools=(),
)


class ManagerAgent:
    """Planner/delegator with no operational tools."""

    profile = MANAGER_PROFILE

    def __init__(
        self,
        planner: RuleBasedPlanner,
    ) -> None:
        self.planner = planner

    def plan(
        self,
        state: AgentState,
    ) -> PlanDecision:
        """Build a plan without executing specialist tools."""
        return self.planner.plan(state)
