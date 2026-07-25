"""Terminal node for a DENY decision: TDD §11's "unsafe request" case —
short-circuits the remaining plan rather than skipping just this step."""
from typing import Any


def deny(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "execute_result": {"success": False, "error": "denied_by_policy"},
        "verification": {"verified": False, "postcondition_met": False, "anomaly_flag": False},
        "terminate_task": True,
    }
