"""Planner node (component 04): transcript + context -> TaskPlan."""
from typing import Any

from components.c04_planner.src.planner import plan as plan_task


def plan(state: dict[str, Any]) -> dict[str, Any]:
    context = state.get("context") or {"open_files": [], "working_memory": {}}
    result = plan_task({"transcript": state["transcript"], "context": context})
    return {"plan": result, "step_index": 0}
