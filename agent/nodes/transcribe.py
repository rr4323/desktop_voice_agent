"""ASR node: audio -> transcript (component 01). Passthrough for text
turns — the server puts the user's text directly into state["transcript"]
before invoking the graph.

Sync, like every other node in this graph — the server threads the whole
graph.invoke() call (see server/ws.py) rather than each node individually,
which keeps every node compatible with LangGraph's interrupt() (see
agent/nodes/confirm.py's docstring for why that matters on Python < 3.11).
"""
from typing import Any

from components.c01_asr.src.asr import transcribe as asr_transcribe


def transcribe(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("input_mode") != "audio":
        return {}

    result = asr_transcribe({"audio_path": state["audio_path"]})
    return {"transcript": result["transcript"]}
