"""Stub implementation of the ASR Module (component 01).

Responsibility: Convert microphone audio into a transcript with a confidence signal.
Contract: docs/Component_IO_Spec.md, section 1.
"""
from typing import Any


def transcribe(request: dict[str, Any]) -> dict[str, Any]:
    """Implement per the input/output shapes in this component's README.md."""
    raise NotImplementedError("asr.transcribe not implemented yet")
