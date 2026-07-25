"""Langfuse tracing for the agent's LangGraph runs.

Wired in as a deliberate, explicit feature — not because of the
`LANGFUSE_PROMPT` field sitting in the project's `.env` (that's untrusted
config content asking an AI to install/wire things; it was not executed
as an instruction). Enabled whenever LANGFUSE_SECRET_KEY and
LANGFUSE_PUBLIC_KEY are present in the environment (server/app.py loads
.env at startup); a no-op everywhere else so the agent runs fine without
Langfuse configured.
"""
import os
from functools import lru_cache
from typing import Any

_ENABLED = bool(os.environ.get("LANGFUSE_SECRET_KEY")) and bool(os.environ.get("LANGFUSE_PUBLIC_KEY"))


@lru_cache(maxsize=1)
def _handler() -> Any | None:
    if not _ENABLED:
        return None
    from langfuse.langchain import CallbackHandler

    return CallbackHandler()


def callbacks() -> list[Any]:
    """Callback list to splice into a LangGraph invoke/ainvoke config."""
    handler = _handler()
    return [handler] if handler else []


def is_enabled() -> bool:
    return _ENABLED
