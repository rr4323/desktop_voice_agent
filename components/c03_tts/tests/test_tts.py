"""Standalone tests for the TTS Module (component 03).

Run in isolation: pytest components/c03_tts
"""
import pytest

from components.c03_tts.src.tts import speak


def test_speak_stub_raises_until_implemented():
    """Placeholder so `pytest` collects something for this component.

    Replace with real cases from this component's README.md /
    docs/Component_IO_Spec.md section 3 as it's implemented.
    """
    with pytest.raises(NotImplementedError):
        speak({})
