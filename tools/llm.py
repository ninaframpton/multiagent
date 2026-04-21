"""LLM helper — wraps the Google Gemini API via google-genai.

Set GOOGLE_API_KEY in .env. The model defaults to gemini-2.0-flash but can
be overridden via the GEMINI_MODEL env var.

Usage
-----
    from tools.llm import ask

    reply = await ask("List 5 indie artists as JSON.")
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
import google.genai as genai

load_dotenv()

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.0-flash"


def _client() -> genai.Client:
    """Return a configured Gemini client.

    Raises:
        RuntimeError: If GOOGLE_API_KEY is not set in .env.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Add it to your .env file.\n"
            "Get a key at: https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=api_key)


async def ask(
    prompt: str,
    system: str = "You are a helpful assistant.",
    model: str | None = None,
) -> str:
    """Send a prompt to Gemini and return the text reply.

    Args:
        prompt: The user message.
        system: Optional system instruction for context.
        model: Model override. Defaults to GEMINI_MODEL env var or gemini-2.0-flash.

    Returns:
        The model's text response as a plain string.

    Raises:
        RuntimeError: If GOOGLE_API_KEY is not set in .env.
    """
    resolved_model = model or os.getenv("GEMINI_MODEL", _DEFAULT_MODEL)
    client = _client()

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=resolved_model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=system,
        ),
    )
    return response.text.strip()
