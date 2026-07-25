"""Audit node (component 12) + state manager (component 11): one masked
log entry per step, and the step-loop's own advance/stop decision."""
from typing import Any

from components.c11_state_manager.src.state_manager import apply_operation
from components.c12_audit_logger.src.audit_logger import log_entry


def _confirmation_label(state: dict[str, Any]) -> str:
    if state["current_decision"]["decision"] != "ASK_CONFIRM":
        return "n/a"
    return "user_approved" if state.get("confirmed") else "user_declined"


def audit(state: dict[str, Any]) -> dict[str, Any]:
    step = state["current_step"]
    decision = state["current_decision"]
    result = state.get("execute_result") or {}
    verification = state.get("verification") or {"verified": True, "postcondition_met": True, "anomaly_flag": False}
    task_id = state["task_id"]

    log_entry(
        {
            "transcript_snippet": state["transcript"],
            "action": step,
            "decision": decision,
            "confirmation": _confirmation_label(state),
            "result": "success" if result.get("success", True) else "failed",
            "verification": "pass" if verification.get("postcondition_met") else "fail",
        }
    )

    apply_operation(
        {
            "operation": "update_status",
            "task_id": task_id,
            "step_id": step["step_id"],
            "status": "done" if verification.get("postcondition_met") else "failed",
        }
    )

    terminate = bool(state.get("terminate_task"))
    next_index = state["step_index"] + 1
    steps = state["plan"]["steps"]
    done = terminate or next_index >= len(steps)

    return {
        "results": [{"step": step, "decision": decision, "result": result, "verification": verification}],
        "step_index": next_index,
        "done": done,
    }
