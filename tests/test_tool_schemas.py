"""Unit tests for typed agent tool schemas."""

import pytest
from pydantic import ValidationError

from app.storage.models import (
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
)
from app.tools.schemas import (
    AppendIncidentNoteDraft,
    AppendIncidentNoteInput,
    CreateIncidentInput,
    SearchIncidentsInput,
)


def test_create_incident_input_accepts_valid_payload():
    payload = CreateIncidentInput(
        title="Problema MFA",
        description="Usuario perdió su autenticador.",
        category="access",
        severity="medium",
    )

    assert payload.category == IncidentCategory.ACCESS
    assert payload.severity == IncidentSeverity.MEDIUM


def test_create_incident_input_rejects_invalid_category():
    with pytest.raises(ValidationError):
        CreateIncidentInput(
            title="Problema",
            description="Descripción",
            category="invented-category",
            severity="medium",
        )


def test_create_incident_input_rejects_blank_title():
    with pytest.raises(ValidationError):
        CreateIncidentInput(
            title="   ",
            description="Descripción válida",
            category="access",
            severity="low",
        )


def test_search_incidents_input_validates_limit_and_status():
    payload = SearchIncidentsInput(
        query="MFA",
        status="open",
        limit=5,
    )

    assert payload.status == IncidentStatus.OPEN
    assert payload.limit == 5

    with pytest.raises(ValidationError):
        SearchIncidentsInput(limit=1000)


def test_append_incident_note_rejects_blank_note():
    with pytest.raises(ValidationError):
        AppendIncidentNoteInput(
            incident_id="INC-00001",
            note="   ",
        )


def test_append_incident_note_draft_allows_memory_resolved_incident():
    payload = AppendIncidentNoteDraft(
        note="Identidad del usuario validada."
    )

    assert payload.incident_id is None
    assert payload.note == "Identidad del usuario validada."


def test_append_incident_note_draft_rejects_blank_note():
    with pytest.raises(ValidationError):
        AppendIncidentNoteDraft(
            note="   "
        )
