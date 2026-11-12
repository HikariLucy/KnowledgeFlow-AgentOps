"""Manual integration test script for Gemini Chat Generation.

This script tests live connectivity to Google Gemini Chat API when GEMINI_API_KEY is configured.
It is isolated from automated unit tests and never dumps secret keys.
"""

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.config import get_settings
from app.llm.client import get_gemini_client


def run_live_chat_check() -> None:
    """Execute a real test call against Gemini Chat API."""
    settings = get_settings()
    gemini_client = get_gemini_client(settings)

    if not gemini_client.is_configured:
        print("========================================")
        print("    Gemini Live Chat Verification       ")
        print("========================================")
        print("Status: SKIPPED")
        print(
            "Reason: GEMINI_API_KEY is not configured in your environment or .env file."
        )
        print("========================================")
        return

    print("========================================")
    print("    Gemini Live Chat Verification       ")
    print("========================================")
    print(f"Chat Model:  {settings.gemini_chat_model}")
    print(f"Temperature: {settings.llm_temperature}")

    try:
        from google.genai import types

        client = gemini_client.get_client()
        config = types.GenerateContentConfig()
        if settings.llm_temperature is not None:
            config.temperature = settings.llm_temperature

        response = client.models.generate_content(
            model=settings.gemini_chat_model,
            contents="Responde únicamente con la palabra 'CONECTADO'.",
            config=config,
        )

        if not response or not response.text:
            print("Status: FAILED (Empty response)")
            sys.exit(1)

        print("Status:      SUCCESS")
        print(f"Response:    {response.text.strip()}")
        print("========================================")

    except Exception as e:
        print("Status:      ERROR")
        print(f"Failed to call Gemini chat: {e}")
        print("========================================")
        sys.exit(1)


if __name__ == "__main__":
    run_live_chat_check()
