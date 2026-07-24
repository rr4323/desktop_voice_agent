"""Standalone tests for the State Manager (component 11).

Run in isolation: pytest components/c11_state_manager
"""
import pytest

from components.c11_state_manager.src.state_manager import apply_operation


def test_apply_operation_stub_raises_until_implemented():
    """Placeholder so `pytest` collects something for this component.

    Replace with real cases from this component's README.md /
    docs/Component_IO_Spec.md section 11 as it's implemented.
    """
    with pytest.raises(NotImplementedError):
        apply_operation({})
