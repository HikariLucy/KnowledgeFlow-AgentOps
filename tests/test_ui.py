"""Offline unit tests for KnowledgeFlow RAG UI endpoints and static asset serving."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ui_root_endpoint_serves_html():
    """Verify GET / returns 200 with HTML content."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "KnowledgeFlow" in response.text
    assert "Consulta de conocimiento" in response.text
    assert "QUERY / 01" in response.text
    assert "MOTOR DE CONOCIMIENTO" in response.text
    assert "CONSULTAS DE REFERENCIA" in response.text
    assert "EVIDENCIA RECUPERADA" in response.text.upper()


def test_ui_static_styles_accessible():
    """Verify GET /static/styles.css returns 200 with CSS content."""
    response = client.get("/static/styles.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")
    assert "--bg-canvas" in response.text
    assert "prov-internal" in response.text
    assert "prov-external" in response.text


def test_ui_static_app_js_accessible():
    """Verify the UI JavaScript is served and preserves safe citation rendering."""
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers.get("content-type", "")
    assert "renderGroundedText" in response.text
    assert "highlightEvidenceItem" in response.text
    assert "document.createTextNode" in response.text
    assert "innerHTML" not in response.text
    assert "aria-controls" in response.text


def test_ui_static_missing_file_returns_404():
    """Verify GET /static/non_existent.txt returns 404."""
    response = client.get("/static/non_existent.txt")
    assert response.status_code == 404


def test_health_endpoint_preserved():
    """Verify GET /health remains functional after UI mounting."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_openapi_docs_preserved():
    """Verify GET /docs remains accessible for API discovery."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
