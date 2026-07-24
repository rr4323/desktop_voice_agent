"""Standalone tests for the Policy Engine (component 05).

Run in isolation: pytest components/c05_policy_engine
"""
import pytest

from components.c05_policy_engine.src.policy_engine import evaluate


def test_evaluate_stub_raises_until_implemented():
    """Placeholder so `pytest` collects something for this component.

    Replace with real cases from this component's README.md /
    docs/Component_IO_Spec.md section 5 as it's implemented.
    """
    with pytest.raises(NotImplementedError):
        evaluate({})
