"""Standalone tests for the Orchestrator (component 13).

Run in isolation: pytest components/c13_orchestrator
"""
import pytest

from components.c13_orchestrator.src.orchestrator import run_task


def test_run_task_stub_raises_until_implemented():
    """Placeholder so `pytest` collects something for this component.

    Replace with real cases from this component's README.md /
    docs/Component_IO_Spec.md section 13 as it's implemented.
    """
    with pytest.raises(NotImplementedError):
        run_task({})
