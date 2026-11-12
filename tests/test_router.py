"""Offline unit tests for Source Routing Agent."""

from unittest.mock import MagicMock
import pytest

from app.agents.source_router import (
    BaseSourceRouter,
    FakeSourceRouter,
    GeminiSourceRouter,
)
from app.rag.schemas import RouteDecision


def test_fake_source_router_internal():
    """Verify router classifies internal queries correctly."""
    router = FakeSourceRouter()
    decision = router.route("¿Cuál es la política interna de contraseñas de NovaTech?")
    assert decision.source_scope == "internal"
    assert 0.0 <= decision.confidence <= 1.0


def test_fake_source_router_external():
    """Verify router classifies external standards queries correctly."""
    router = FakeSourceRouter()
    decision = router.route("¿Qué vulnerabilidades describe el estándar OWASP Top 10?")
    assert decision.source_scope == "external"
    assert 0.0 <= decision.confidence <= 1.0


def test_fake_source_router_all():
    """Verify router classifies comparative/general queries to 'all'."""
    router = FakeSourceRouter()
    decision = router.route("Compara nuestras políticas frente a las buenas prácticas OWASP")
    assert decision.source_scope == "all"
    assert 0.0 <= decision.confidence <= 1.0


def test_fake_source_router_empty_query():
    """Verify empty query falls back to 'all'."""
    router = FakeSourceRouter()
    decision = router.route("")
    assert decision.source_scope == "all"
    assert decision.confidence == 0.5


def test_gemini_source_router_valid_internal():
    """Verify GeminiSourceRouter handles valid internal structured JSON response."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"source_scope": "internal", "confidence": 0.94, "routing_reason": "Pregunta sobre políticas internas."}'
    mock_sdk_client.models.generate_content.return_value = mock_response
    mock_client.get_client.return_value = mock_sdk_client

    router = GeminiSourceRouter(gemini_client=mock_client)
    decision = router.route("¿Cómo reporto un incidente?")

    assert decision.source_scope == "internal"
    assert decision.confidence == 0.94
    assert decision.routing_reason == "Pregunta sobre políticas internas."


def test_gemini_source_router_fallback_on_invalid_json():
    """Verify GeminiSourceRouter falls back safely to 'all' on malformed JSON response."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Esto no es JSON válido"
    mock_sdk_client.models.generate_content.return_value = mock_response
    mock_client.get_client.return_value = mock_sdk_client

    router = GeminiSourceRouter(gemini_client=mock_client)
    decision = router.route("Consulta cualquiera")

    assert decision.source_scope == "all"
    assert decision.confidence == 0.50
    assert "Fallback to 'all'" in (decision.routing_reason or "")


def test_gemini_source_router_fallback_on_invalid_scope():
    """Verify GeminiSourceRouter falls back safely when LLM returns an unknown source_scope."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"source_scope": "confidential_cloud", "confidence": 0.99}'
    mock_sdk_client.models.generate_content.return_value = mock_response
    mock_client.get_client.return_value = mock_sdk_client

    router = GeminiSourceRouter(gemini_client=mock_client)
    decision = router.route("Consulta con scope inventado")

    assert decision.source_scope == "all"
    assert decision.confidence == 0.50


def test_gemini_source_router_fallback_on_low_confidence():
    """Verify GeminiSourceRouter falls back to 'all' when confidence is below threshold."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"source_scope": "internal", "confidence": 0.20, "routing_reason": "Baja certeza"}'
    mock_sdk_client.models.generate_content.return_value = mock_response
    mock_client.get_client.return_value = mock_sdk_client

    router = GeminiSourceRouter(gemini_client=mock_client, min_confidence=0.40)
    decision = router.route("Pregunta ambigua")

    assert decision.source_scope == "all"
