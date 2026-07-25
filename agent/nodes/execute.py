"""Execute node: dispatches the current (already policy-approved) step to
the matching tool (tools/registry.py) and stores any extracted value into
working memory (component 09) so later steps can reference it by key
instead of the planner re-typing/re-deriving it."""
from typing import Any

from components.c09_working_memory.src.working_memory import set_or_get
from tools.registry import get_tool


def execute(state: dict[str, Any]) -> dict[str, Any]:
    step = state["current_step"]
    task_id = state["task_id"]

    try:
        print(step)
        tool = get_tool(step["target"]["app"])
        print(tool)
        result = tool.run(step)
    except Exception as exc:  # noqa: BLE001 - a bad/incomplete step (e.g. a
        # target missing a field the planner should have filled in, or a
        # LookupError for an unknown app) must fail this step cleanly, not
        # crash the whole graph run/websocket connection over one bad step.
        return {"execute_result": {"success": False, "error": str(exc)}}

    if "value" in result and result["value"] is not None:
        set_or_get(
            {
                "operation": "set",
                "task_id": task_id,
                "key": f"step_{step['step_id']}.value",
                "value": result["value"],
                "provenance": result.get("provenance", {}),
            }
        )

    return {"execute_result": result}
