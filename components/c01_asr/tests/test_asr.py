"""Standalone tests for the ASR Module (component 01).

Run in isolation: pytest components/c01_asr
"""
import pytest

from components.c01_asr.src.asr import transcribe


def test_transcribe_stub_raises_until_implemented():
    """Placeholder so `pytest` collects something for this component.

    Replace with real cases from this component's README.md /
    docs/Component_IO_Spec.md section 1 as it's implemented.
    """
    with pytest.raises(NotImplementedError):
        transcribe({})
