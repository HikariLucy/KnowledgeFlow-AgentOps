"""Source Routing Agent for classifying user queries into internal, external, or all sources."""

from abc import ABC, abstractmethod
import json
import logging
from typing import Callable, Optional

from app.core.config import Settings, get_settings
from app.llm.client import GeminiClient, get_gemini_client
from app.rag.schemas import RouteDecision, SourceScope

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_INSTRUCTION = (
    "Eres un clasificador de consultas para un motor RAG corporativo.\n"
    "Tu única tarea es determinar el alcance de búsqueda ('source_scope') de la consulta.\n\n"
    "Categorías de alcance:\n"
    "1. 'internal': Preguntas sobre políticas internas de la empresa, procedimientos operativos, "
    "gestión de accesos, contraseñas, protocolos de incidentes corporativos o normativas internas.\n"
    "2. 'external': Preguntas sobre estándares de la industria (OWASP, NIST, ISO), guías técnicas generales "
    "o marcos de ciberseguridad externos.\n"
    "3. 'all': Consultas comparativas entre políticas internas y estándares externos, o consultas donde no esté "
    "claro el origen y se requiera consultar todo el conocimiento.\n\n"
    "Debes responder ÚNICAMENTE un objeto JSON válido con los siguientes campos:\n"
    "- 'source_scope': 'internal', 'external', o 'all'\n"
    "- 'confidence': número flotante entre 0.0 y 1.0\n"
    "- 'routing_reason': una breve oración explicando la clasificación."
)


class BaseSourceRouter(ABC):
    """Abstract base interface for source routing agent."""

    @abstractmethod
    def route(self, query: str) -> RouteDecision:
        """Classify query into a RouteDecision ('internal', 'external', or 'all')."""
        pass


class GeminiSourceRouter(BaseSourceRouter):
    """Gemini-powered Source Routing Agent using structured JSON output."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        gemini_client: Optional[GeminiClient] = None,
        min_confidence: float = 0.40,
    ):
        self.settings = settings or get_settings()
        self.gemini_client = gemini_client or get_gemini_client(self.settings)
        self.min_confidence = min_confidence

    def _fallback_decision(self, reason: str) -> RouteDecision:
        """Safe fallback to 'all' source scope."""
        logger.warning("Routing fallback triggered: %s", reason)
        return RouteDecision(
            source_scope="all",
            confidence=0.50,
            routing_reason=f"Fallback to 'all': {reason}",
        )

    def route(self, query: str) -> RouteDecision:
        """Route user query to appropriate source scope using Gemini."""
        if not query or not str(query).strip():
            return self._fallback_decision("Empty query provided.")

        try:
            from google.genai import types

            client = self.gemini_client.get_client()

            config = types.GenerateContentConfig(
                system_instruction=ROUTER_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
            )
            if self.settings.llm_temperature is not None:
                config.temperature = self.settings.llm_temperature

            prompt = f"Consulta del usuario: {query.strip()}"
            import time

            response = None
            for attempt in range(4):
                try:
                    response = client.models.generate_content(
                        model=self.settings.gemini_router_model,
                        contents=prompt,
                        config=config,
                    )
                    if response and response.text:
                        break
                except Exception as ex:
                    if attempt < 3:
                        sleep_time = 3.0 * (attempt + 1)
                        if "429" in str(ex) or "RESOURCE_EXHAUSTED" in str(ex):
                            sleep_time = 8.0 * (attempt + 1)
                        logger.warning(
                            "GeminiSourceRouter attempt %d failed (%s). Retrying in %.1fs...",
                            attempt + 1,
                            ex,
                            sleep_time,
                        )
                        time.sleep(sleep_time)
                        continue
                    raise ex

            if not response or not response.text:
                return self._fallback_decision("Empty response from Gemini router.")

            # Parse JSON output
            data = json.loads(response.text.strip())

            # Validate source_scope
            raw_scope = str(data.get("source_scope", "")).lower().strip()
            if raw_scope not in ("internal", "external", "all"):
                return self._fallback_decision(
                    f"Invalid source_scope '{raw_scope}' in response."
                )

            # Validate confidence
            try:
                conf = float(data.get("confidence", 0.5))
                conf = max(0.0, min(1.0, conf))
            except (ValueError, TypeError):
                conf = 0.5

            if conf < self.min_confidence:
                return self._fallback_decision(
                    f"Confidence ({conf:.2f}) below threshold ({self.min_confidence:.2f})."
                )

            reason = data.get("routing_reason")
            if reason:
                reason = str(reason).strip()

            return RouteDecision(
                source_scope=raw_scope,  # type: ignore
                confidence=conf,
                routing_reason=reason,
            )

        except Exception as e:
            return self._fallback_decision(f"Exception during routing: {e}")


class FakeSourceRouter(BaseSourceRouter):
    """Deterministic offline router for unit testing without network calls."""

    def __init__(
        self,
        custom_router: Optional[Callable[[str], RouteDecision]] = None,
        default_scope: Optional[SourceScope] = None,
    ):
        self.custom_router = custom_router
        self.default_scope = default_scope

    def route(self, query: str) -> RouteDecision:
        """Route deterministically using custom rule, keyword matching, or default scope."""
        if not query or not str(query).strip():
            return RouteDecision(
                source_scope="all",
                confidence=0.5,
                routing_reason="Empty query fallback.",
            )

        if self.custom_router:
            return self.custom_router(query)

        if self.default_scope:
            return RouteDecision(
                source_scope=self.default_scope,
                confidence=0.95,
                routing_reason=f"Configured default {self.default_scope}.",
            )

        q_lower = query.lower()

        # Keywords for comparison or both -> 'all'
        if any(w in q_lower for w in ("ambas", "todos", "compara", "diferencia", "frente a", "vs")):
            return RouteDecision(
                source_scope="all",
                confidence=0.90,
                routing_reason="Detected comparative query keywords.",
            )

        # Keywords for internal
        if any(w in q_lower for w in ("interna", "politica", "política", "acceso", "procedimiento", "password", "contraseña", "incidente", "novatech", "rrhh", "guardia")):
            return RouteDecision(
                source_scope="internal",
                confidence=0.95,
                routing_reason="Detected internal organization keywords.",
            )

        # Keywords for external
        if any(w in q_lower for w in ("externa", "owasp", "nist", "iso", "estándar", "estandar", "vulnerabilidad", "buenas prácticas", "buenas practicas", "marco")):
            return RouteDecision(
                source_scope="external",
                confidence=0.95,
                routing_reason="Detected external standards keywords.",
            )

        return RouteDecision(
            source_scope="all",
            confidence=0.60,
            routing_reason="Default general routing to all.",
        )
