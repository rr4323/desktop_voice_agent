"""Standalone tests for the Task Planner (LLM) (component 04).

Run in isolation: pytest components/c04_planner
"""
import pytest

from components.c04_planner.src.planner import plan


def test_plan_stub_raises_until_implemented():
    """Placeholder so `pytest` collects something for this component.

    Replace with real cases from this component's README.md /
    docs/Component_IO_Spec.md section 4 as it's implemented.
    """
    with pytest.raises(NotImplementedError):
        plan({})
