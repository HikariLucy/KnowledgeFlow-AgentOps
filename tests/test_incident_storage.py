"""Offline tests for SQLite incident persistence."""

import pytest

from app.storage.database import SQLiteDatabase
from app.storage.models import (
    IncidentCategory,
    IncidentCreate,
    IncidentNoteCreate,
    IncidentSeverity,
    IncidentStatus,
)
from app.storage.repositories import IncidentRepository


@pytest.fixture
def incident_repository(tmp_path):
    database = SQLiteDatabase(tmp_path / "knowledgeflow-test.db")
    database.initialize()
    return IncidentRepository(database)


def _incident(
    title: str = "Pérdida de segundo factor",
    status: IncidentStatus = IncidentStatus.OPEN,
) -> IncidentCreate:
    return IncidentCreate(
        title=title,
        description="Usuario perdió el dispositivo utilizado para MFA.",
        category=IncidentCategory.ACCESS,
        severity=IncidentSeverity.MEDIUM,
        status=status,
    )


def test_database_creates_incident_tables(tmp_path):
    database = SQLiteDatabase(tmp_path / "schema.db")
    database.initialize()

    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

    names = {row["name"] for row in rows}

    assert "incidents" in names
    assert "incident_notes" in names


def test_create_incident_generates_public_id(incident_repository):
    incident = incident_repository.create_incident(_incident())

    assert incident.id == 1
    assert incident.public_id == "INC-00001"
    assert incident.category == IncidentCategory.ACCESS
    assert incident.severity == IncidentSeverity.MEDIUM
    assert incident.status == IncidentStatus.OPEN


def test_get_incident_returns_persisted_record(incident_repository):
    created = incident_repository.create_incident(_incident())

    loaded = incident_repository.get_incident(created.public_id)

    assert loaded is not None
    assert loaded.public_id == created.public_id
    assert loaded.title == "Pérdida de segundo factor"


def test_search_incidents_matches_text(incident_repository):
    incident_repository.create_incident(_incident())
    incident_repository.create_incident(
        _incident(title="Error de impresora corporativa")
    )

    results = incident_repository.search_incidents(query="segundo factor")

    assert len(results) == 1
    assert results[0].title == "Pérdida de segundo factor"


def test_search_incidents_filters_status(incident_repository):
    incident_repository.create_incident(
        _incident(
            title="Incidente abierto",
            status=IncidentStatus.OPEN,
        )
    )
    incident_repository.create_incident(
        _incident(
            title="Incidente resuelto",
            status=IncidentStatus.RESOLVED,
        )
    )

    results = incident_repository.search_incidents(
        status=IncidentStatus.RESOLVED
    )

    assert len(results) == 1
    assert results[0].status == IncidentStatus.RESOLVED


def test_append_and_list_incident_note(incident_repository):
    incident = incident_repository.create_incident(_incident())

    note = incident_repository.append_note(
        incident.public_id,
        IncidentNoteCreate(
            note="Se validó identidad del usuario antes de continuar."
        ),
    )

    notes = incident_repository.list_notes(incident.public_id)

    assert note.incident_public_id == incident.public_id
    assert len(notes) == 1
    assert notes[0].note == (
        "Se validó identidad del usuario antes de continuar."
    )


def test_append_note_rejects_unknown_incident(incident_repository):
    with pytest.raises(ValueError, match="Incident not found"):
        incident_repository.append_note(
            "INC-99999",
            IncidentNoteCreate(note="Nota inválida"),
        )
