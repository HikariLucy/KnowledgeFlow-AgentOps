"""Decoupled Google Gemini client integration."""

from typing import Optional
from app.core.config import Settings, get_settings


class GeminiClient:
    """Wrapper for Google Gemini services, decoupled from core RAG logic."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._api_key = self.settings.gemini_api_key
        self.chat_model_name = self.settings.gemini_chat_model
        self.embedding_model_name = self.settings.gemini_embedding_model
        self._client = None

    @property
    def is_configured(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self._api_key and self._api_key.strip())

    def get_client(self):
        """Retrieve underlying Google GenAI client instance.

        Raises:
            RuntimeError: If GEMINI_API_KEY is not configured.
        """
        if not self.is_configured:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured. Set GEMINI_API_KEY in the environment or .env file."
            )

        if self._client is None:
            try:
                from google import genai

                self._client = genai.Client(api_key=self._api_key)
            except ImportError as e:
                raise RuntimeError(
                    "google-genai package is required to use Gemini services."
                ) from e

        return self._client


def get_gemini_client(settings: Optional[Settings] = None) -> GeminiClient:
    """Factory function for GeminiClient."""
    return GeminiClient(settings=settings)
