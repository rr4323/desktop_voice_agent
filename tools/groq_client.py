"""Minimal shared Groq chat-completion helper for tools that need a
one-shot structured-JSON completion (e.g. turning raw text into a slide
outline before creating a deck) — the same direct-HTTP approach
components/c04_planner uses, not a full SDK, kept here so multiple tools
don't each duplicate the request-building/auth boilerplate.

This is distinct from components/c17_browser_agent's ChatGroq usage (a
multi-step LangGraph ReAct loop) and does not perform web search itself —
see tools/sub_agent/browser_agent_tool.py for that.
"""
import json
import os

import requests

_GROQ_BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
_GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
_DEFAULT_MODEL = os.environ.get("GROQ_STRUCTURING_MODEL", "openai/gpt-oss-120b")
_TIMEOUT_S = float(os.environ.get("GROQ_TIMEOUT_S", "30"))


def structured_completion(system_prompt: str, user_prompt: str, model: str | None = None) -> dict:
    """One JSON-mode chat completion, parsed and returned as a dict.
    Raises RuntimeError if GROQ_API_KEY isn't set, requests.RequestException
    on network/HTTP failure, or json.JSONDecodeError on a non-JSON reply —
    callers decide how to degrade, same pattern as c04_planner.plan()."""
    if not _GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    response = requests.post(
        f"{_GROQ_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {_GROQ_API_KEY}"},
        json={
            "model": model or _DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        },
        timeout=_TIMEOUT_S,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)
