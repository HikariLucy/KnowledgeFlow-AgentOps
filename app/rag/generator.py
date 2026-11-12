"""Grounded RAG answer generation with Google Gemini and citation validation."""

from abc import ABC, abstractmethod
import logging
from typing import Callable, List, Optional, Set, Tuple

from app.core.config import Settings, get_settings
from app.llm.client import GeminiClient, get_gemini_client
from app.rag.context import extract_citations_from_text, validate_citations
from app.rag.prompts import RAG_SYSTEM_PROMPT, format_rag_user_prompt
from app.rag.schemas import SourceReference, SourceScope

logger = logging.getLogger(__name__)


class BaseRAGGenerator(ABC):
    """Abstract interface for RAG answer generators."""

    @abstractmethod
    def generate(
        self,
        query: str,
        context_str: str,
        source_references: List[SourceReference],
        source_scope: SourceScope = "all",
    ) -> Tuple[str, List[str], bool]:
        """Generate a grounded answer for the user query using retrieved context.

        Args:
            query: User question.
            context_str: Formatted context blocks [S1]..[SN].
            source_references: List of active SourceReferences for citation validation.
            source_scope: Classification scope used.

        Returns:
            Tuple of (answer_text, citations_list, is_grounded_bool).
        """
        pass


class GeminiRAGGenerator(BaseRAGGenerator):
    """Google Gemini RAG generator with structured grounding and citation verification."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        gemini_client: Optional[GeminiClient] = None,
    ):
        self.settings = settings or get_settings()
        self.gemini_client = gemini_client or get_gemini_client(self.settings)

    def _call_gemini(self, user_prompt: str) -> str:
        """Call Gemini chat model with system instruction and configured settings."""
        from google.genai import types
        import time

        client = self.gemini_client.get_client()
        config = types.GenerateContentConfig(
            system_instruction=RAG_SYSTEM_PROMPT,
        )
        if self.settings.llm_temperature is not None:
            config.temperature = self.settings.llm_temperature

        response = None
        for attempt in range(4):
            try:
                response = client.models.generate_content(
                    model=self.settings.gemini_chat_model,
                    contents=user_prompt,
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
                        "GeminiRAGGenerator attempt %d failed (%s). Retrying in %.1fs...",
                        attempt + 1,
                        ex,
                        sleep_time,
                    )
                    time.sleep(sleep_time)
                    continue
                raise ex

        if not response or not response.text:
            raise RuntimeError("Empty response from Gemini generation model.")

        return response.text.strip()

    def generate(
        self,
        query: str,
        context_str: str,
        source_references: List[SourceReference],
        source_scope: SourceScope = "all",
    ) -> Tuple[str, List[str], bool]:
        """Generate grounded answer, validate citations, and attempt 1 repair if phantom citations exist."""
        valid_ids: Set[str] = {ref.id for ref in source_references}
        user_prompt = format_rag_user_prompt(context_str, query)

        # 1. First generation attempt
        answer_text = self._call_gemini(user_prompt)

        # 2. Validate citations
        is_valid, valid_citations, phantom_citations = validate_citations(
            answer_text, valid_ids
        )

        if is_valid:
            return answer_text, valid_citations, True

        # 3. Attempt 1 controlled repair if citations were invalid or missing
        sorted_valid = ", ".join(sorted(valid_ids))
        if phantom_citations:
            reason = f"utilizaste citas inexistentes: {phantom_citations}"
        else:
            reason = "no incluiste ninguna cita documental obligatoria [S#] de la evidencia provista"

        logger.warning(
            "Generation citation validation failed (%s). Attempting 1 repair...",
            reason,
        )
        repair_prompt = (
            f"{user_prompt}\n\n"
            f"[ADVERTENCIA DE CORRECCIÓN]: En el intento anterior {reason}. "
            f"Vuelve a generar la respuesta fundamentando tus afirmaciones e incluyendo al menos una cita válida entre: [{sorted_valid}]. "
            f"Si algún dato no está en esas fuentes, no lo incluyas."
        )

        try:
            repaired_text = self._call_gemini(repair_prompt)
            is_valid_repaired, rep_valid_cits, rep_phantoms = validate_citations(
                repaired_text, valid_ids
            )
            if is_valid_repaired:
                return repaired_text, rep_valid_cits, True
        except Exception as e:
            logger.error("Error during citation repair attempt: %s", e)

        # 4. If repair still failed or threw an error, return controlled fallback
        fallback_text = (
            "No fue posible generar una respuesta con trazabilidad verificable debido a inconsistencias "
            "en las referencias documentales generadas. Por favor consulta las fuentes recuperadas directamente."
        )
        return fallback_text, [], False


class FakeRAGGenerator(BaseRAGGenerator):
    """Deterministic offline generator for unit tests."""

    def __init__(
        self,
        custom_generator: Optional[
            Callable[[str, str, List[SourceReference]], Tuple[str, List[str], bool]]
        ] = None,
        force_phantom_citation: bool = False,
    ):
        self.custom_generator = custom_generator
        self.force_phantom_citation = force_phantom_citation

    def generate(
        self,
        query: str,
        context_str: str,
        source_references: List[SourceReference],
        source_scope: SourceScope = "all",
    ) -> Tuple[str, List[str], bool]:
        """Generate deterministic fake grounded response."""
        if self.custom_generator:
            return self.custom_generator(query, context_str, source_references)

        if not source_references:
            return (
                "No encontré evidencia suficiente en las fuentes disponibles para responder esta consulta.",
                [],
                True,
            )

        valid_ids = [ref.id for ref in source_references]

        if self.force_phantom_citation:
            # Generate invalid citation for testing validation & repair rejection
            text = "Respuesta con referencia inexistente [S99]."
            valid_set = set(valid_ids)
            is_valid, cits, _ = validate_citations(text, valid_set)
            return text, cits, False

        citations = [valid_ids[0]]
        text = f"Según la evidencia documental provista, la respuesta a '{query}' está validada [{citations[0]}]."
        return text, citations, True
