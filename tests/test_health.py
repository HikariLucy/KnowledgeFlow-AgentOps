"""Tests for health check endpoint."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_status_code():
    """Verify GET /health returns HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_payload():
    """Verify GET /health returns expected status and service name."""
    response = client.get("/health")
    data = response.json()
    assert data == {
        "status": "ok",
        "service": "KnowledgeFlow RAG",
    }
