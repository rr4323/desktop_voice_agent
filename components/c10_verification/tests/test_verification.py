"""Standalone tests for the Verification Module (component 10).

Run in isolation: pytest components/c10_verification
"""
import pytest

from components.c10_verification.src.verification import verify


def test_verify_stub_raises_until_implemented():
    """Placeholder so `pytest` collects something for this component.

    Replace with real cases from this component's README.md /
    docs/Component_IO_Spec.md section 10 as it's implemented.
    """
    with pytest.raises(NotImplementedError):
        verify({})
