"""Policy engine node (component 05): the sole authority deciding
ALLOW / ASK_CONFIRM / DENY for the current step. Pure/deterministic."""
from typing import Any

from components.c05_policy_engine.src.policy_engine import evaluate

from agent.nodes._helpers import peek_current_value, resolve_step_value


def _dependency_failure(state: dict[str, Any], step: dict[str, Any]) -> dict[str, Any] | None:
    """If a step this one depends_on already failed, its resolved "value"
    would just be working memory's unresolved placeholder string (or None)
    rather than real data — don't let that garbage flow into a tool call.
    Short-circuit through the existing DENY route instead."""
    depends_on = step.get("depends_on") or []
    if not depends_on:
        return None
    results_by_step_id = {r["step"]["step_id"]: r for r in state.get("results", [])}
    for dep_id in depends_on:
        dep_result = results_by_step_id.get(dep_id)
        if dep_result is not None and not dep_result["result"].get("success", True):
            return {
                "step_id": step["step_id"],
                "decision": "DENY",
                "tier": "skipped-dependency-failed",
                "reason": (
                    f"Step {step['step_id']} depends on step {dep_id}, which failed — "
                    "skipping it rather than proceeding with incomplete data."
                ),
            }
    return None


def policy_check(state: dict[str, Any]) -> dict[str, Any]:
    steps = state["plan"]["steps"]
    step = steps[state["step_index"]]

    dep_failure = _dependency_failure(state, step)
    if dep_failure is not None:
        return {"current_step": {**step, "value": None}, "current_decision": dep_failure}

    resolved_value = resolve_step_value(state["task_id"], step)
    current_value = None
    if step["type"] in ("write", "create"):
        current_value = peek_current_value(step)

    request = {
        "step_id": step["step_id"],
        "type": step["type"],
        "target": step["target"],
        "current_cell_value": current_value,
        "value": resolved_value,
    }
    decision = evaluate(request)

    return {"current_step": {**step, "value": resolved_value}, "current_decision": decision}
