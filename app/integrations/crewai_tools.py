"""CrewAI adapters for KnowledgeFlow domain tools."""

import json

from crewai.tools import BaseTool
from pydantic import BaseModel, PrivateAttr

from app.tools.incidents import (
    AppendIncidentNoteTool,
    CreateIncidentTool,
    SearchIncidentsTool,
)
from app.tools.knowledge import KnowledgeRAGTool
from app.tools.schemas import (
    AppendIncidentNoteInput,
    CreateIncidentInput,
    KnowledgeQueryInput,
    SearchIncidentsInput,
)


class CrewAIKnowledgeTool(BaseTool):
    """Expose KnowledgeRAGTool through CrewAI's BaseTool contract."""

    name: str = "search_knowledge"
    description: str = KnowledgeRAGTool.description
    args_schema: type[BaseModel] = KnowledgeQueryInput

    _delegate: KnowledgeRAGTool = PrivateAttr()

    def __init__(self, delegate: KnowledgeRAGTool) -> None:
        super().__init__()
        self._delegate = delegate

    def _run(
        self,
        query: str,
        source_scope=None,
        top_k: int | None = None,
    ) -> str:
        result = self._delegate.run(
            KnowledgeQueryInput(
                query=query,
                source_scope=source_scope,
                top_k=top_k,
            )
        )

        return result.model_dump_json()


class CrewAICreateIncidentTool(BaseTool):
    """Expose validated incident creation to CrewAI."""

    name: str = "create_incident"
    description: str = CreateIncidentTool.description
    args_schema: type[BaseModel] = CreateIncidentInput

    _delegate: CreateIncidentTool = PrivateAttr()

    def __init__(self, delegate: CreateIncidentTool) -> None:
        super().__init__()
        self._delegate = delegate

    def _run(
        self,
        title: str,
        description: str,
        category,
        severity,
    ) -> str:
        result = self._delegate.run(
            CreateIncidentInput(
                title=title,
                description=description,
                category=category,
                severity=severity,
            )
        )

        return result.model_dump_json()


class CrewAISearchIncidentsTool(BaseTool):
    """Expose validated incident search to CrewAI."""

    name: str = "search_incidents"
    description: str = SearchIncidentsTool.description
    args_schema: type[BaseModel] = SearchIncidentsInput

    _delegate: SearchIncidentsTool = PrivateAttr()

    def __init__(self, delegate: SearchIncidentsTool) -> None:
        super().__init__()
        self._delegate = delegate

    def _run(
        self,
        query: str | None = None,
        status=None,
        limit: int = 10,
    ) -> str:
        results = self._delegate.run(
            SearchIncidentsInput(
                query=query,
                status=status,
                limit=limit,
            )
        )

        return json.dumps(
            [
                incident.model_dump(mode="json")
                for incident in results
            ],
            ensure_ascii=False,
        )


class CrewAIAppendIncidentNoteTool(BaseTool):
    """Expose validated incident follow-up to CrewAI."""

    name: str = "append_incident_note"
    description: str = AppendIncidentNoteTool.description
    args_schema: type[BaseModel] = AppendIncidentNoteInput

    _delegate: AppendIncidentNoteTool = PrivateAttr()

    def __init__(
        self,
        delegate: AppendIncidentNoteTool,
    ) -> None:
        super().__init__()
        self._delegate = delegate

    def _run(
        self,
        incident_id: str,
        note: str,
    ) -> str:
        result = self._delegate.run(
            AppendIncidentNoteInput(
                incident_id=incident_id,
                note=note,
            )
        )

        return result.model_dump_json()
