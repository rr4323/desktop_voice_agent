"""Verification node (component 10): re-reads the write target through the
same tool and confirms the postcondition actually holds, rather than
inferring success from the absence of an exception (TDD §6.7)."""
import os
from typing import Any

from components.c10_verification.src.verification import verify as verify_postcondition
from tools.registry import get_tool

_TRIVIALLY_VERIFIED = {"verified": True, "postcondition_met": True, "anomaly_flag": False}
_NOT_VERIFIED = {"verified": False, "postcondition_met": False, "anomaly_flag": False}


def verify(state: dict[str, Any]) -> dict[str, Any]:
    step = state["current_step"]
    result = state.get("execute_result") or {}

    if step["type"] == "create":
        # No prior value to compare against — the postcondition is just
        # "the file genuinely landed on disk", not inferred from a
        # successful return alone (same "re-check, don't trust the
        # exception-free path" principle as the write case below).
        exists = bool(result.get("success")) and os.path.exists(result.get("file", ""))
        return {"verification": {"verified": exists, "postcondition_met": exists, "anomaly_flag": False}}

    if step["type"] != "write":
        return {"verification": _TRIVIALLY_VERIFIED}
    if not result.get("success"):
        return {"verification": _NOT_VERIFIED}

    tool = get_tool(step["target"]["app"])
    try:
        current_read = tool.run({**step, "type": "read"})
    except Exception:  # noqa: BLE001 - a failed re-read means "not verified", not a crash
        return {"verification": _NOT_VERIFIED}

    verification = verify_postcondition(
        {
            "action_result": {"expected_value": result.get("new_value")},
            "current_read": {"value": current_read.get("value")},
            "historical_context": step.get("target", {}).get("historical_context"),
        }
    )
    return {"verification": verification}
