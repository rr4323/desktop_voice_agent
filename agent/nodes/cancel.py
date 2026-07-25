"""Terminal node for a declined confirmation (TDD §11's "cancellation"
case): stops the task with no partial write left unreported."""
from typing import Any


def cancel(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "execute_result": {"success": False, "error": "cancelled_by_user"},
        "verification": {"verified": False, "postcondition_met": False, "anomaly_flag": False},
        "terminate_task": True,
    }
