"""Tests for agent-facing incident tools."""

import pytest

from app.storage.database import SQLiteDatabase
from app.storage.repositories import IncidentRepository
from app.tools.incidents import (
    AppendIncidentNoteTool,
    CreateIncidentTool,
    SearchIncidentsTool,
)
from app.tools.schemas import (
    AppendIncidentNoteInput,
    CreateIncidentInput,
    SearchIncidentsInput,
)


@pytest.fixture
def tools(tmp_path):
    database = SQLiteDatabase(tmp_path / "incident-tools.db")
    database.initialize()

    repository = IncidentRepository(database)

    return {
        "create": CreateIncidentTool(repository),
        "search": SearchIncidentsTool(repository),
        "append": AppendIncidentNoteTool(repository),
    }


def test_create_incident_tool_persists_incident(tools):
    result = tools["create"].run(
        CreateIncidentInput(
            title="Pérdida de autenticador",
            description="Usuario perdió el dispositivo utilizado para MFA.",
            category="access",
            severity="medium",
        )
    )

    assert result.public_id == "INC-00001"
    assert result.title == "Pérdida de autenticador"
    assert result.category.value == "access"
    assert result.severity.value == "medium"
    assert result.status.value == "open"


def test_search_incidents_tool_finds_created_incident(tools):
    tools["create"].run(
        CreateIncidentInput(
            title="Error de acceso VPN",
            description="Usuario no puede acceder a la VPN corporativa.",
            category="access",
            severity="medium",
        )
    )

    results = tools["search"].run(
        SearchIncidentsInput(query="VPN")
    )

    assert len(results) == 1
    assert results[0].title == "Error de acceso VPN"


def test_search_incidents_tool_can_filter_status(tools):
    tools["create"].run(
        CreateIncidentInput(
            title="Incidente abierto",
            description="Caso de prueba.",
            category="other",
            severity="low",
        )
    )

    results = tools["search"].run(
        SearchIncidentsInput(status="open")
    )

    assert len(results) == 1
    assert results[0].status.value == "open"


def test_append_incident_note_tool_persists_follow_up(tools):
    incident = tools["create"].run(
        CreateIncidentInput(
            title="Problema MFA",
            description="Usuario reporta pérdida del autenticador.",
            category="access",
            severity="medium",
        )
    )

    note = tools["append"].run(
        AppendIncidentNoteInput(
            incident_id=incident.public_id,
            note="Identidad del usuario validada.",
        )
    )

    assert note.incident_public_id == incident.public_id
    assert note.note == "Identidad del usuario validada."


def test_append_incident_note_tool_rejects_unknown_incident(tools):
    with pytest.raises(ValueError, match="Incident not found"):
        tools["append"].run(
            AppendIncidentNoteInput(
                incident_id="INC-99999",
                note="Seguimiento inexistente.",
            )
        )
