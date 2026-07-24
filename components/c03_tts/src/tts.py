"""Stub implementation of the TTS Module (component 03).

Responsibility: Convert a response string into spoken audio output, with support for barge-in interruption.
Contract: docs/Component_IO_Spec.md, section 3.
"""
from typing import Any


def speak(request: dict[str, Any]) -> dict[str, Any]:
    """Implement per the input/output shapes in this component's README.md."""
    raise NotImplementedError("tts.speak not implemented yet")
