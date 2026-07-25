"""Gemini LLM client adapter: thin REST wrapper around Google's Generative
Language API, used by handlers/presentation_handler.py for zero-shot
structured-JSON slide planning.

Calls the REST endpoint directly with `requests` (same "no SDK needed for
one structured completion" approach as components/c04_planner's Groq
client) rather than pulling in the google-generativeai/google-genai
package.
"""
import json
import os

import requests

_GEMINI_BASE_URL = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
_TIMEOUT_S = float(os.environ.get("GEMINI_TIMEOUT_S", "60"))


def is_llm_available() -> bool:
    return bool(_GEMINI_API_KEY)


def call_llm(user_content: str, system_instruction: str | None = None, json_mode: bool = False):
    """Single structured-completion call.

    Returns a parsed dict when json_mode is True, a raw string otherwise,
    or None on any failure (no API key, network error, malformed
    response) — callers fall back to their own non-LLM logic rather than
    crashing on this call.
    """
    if not _GEMINI_API_KEY:
        return None

    generation_config = {"temperature": 0}
    if json_mode:
        generation_config["responseMimeType"] = "application/json"

    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_content}]}],
        "generationConfig": generation_config,
    }
    if system_instruction:
        payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

    try:
        response = requests.post(
            f"{_GEMINI_BASE_URL}/models/{_MODEL}:generateContent",
            params={"key": _GEMINI_API_KEY},
            json=payload,
            timeout=_TIMEOUT_S,
        )
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None

    if not json_mode:
        return text

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
