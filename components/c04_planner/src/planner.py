"""Stub implementation of the Task Planner (LLM) (component 04).

Responsibility: Convert a transcript + task context into a structured, schema-valid TaskPlan. Never executes anything itself.
Contract: docs/Component_IO_Spec.md, section 4.
"""
from typing import Any


def plan(request: dict[str, Any]) -> dict[str, Any]:
    """Implement per the input/output shapes in this component's README.md."""
    raise NotImplementedError("planner.plan not implemented yet")
