"""Standalone tests for the Working Memory Store (component 09).

Run in isolation: pytest components/c09_working_memory
"""
import pytest

from components.c09_working_memory.src.working_memory import set_or_get


def test_set_or_get_stub_raises_until_implemented():
    """Placeholder so `pytest` collects something for this component.

    Replace with real cases from this component's README.md /
    docs/Component_IO_Spec.md section 9 as it's implemented.
    """
    with pytest.raises(NotImplementedError):
        set_or_get({})
