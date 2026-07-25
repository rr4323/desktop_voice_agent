"""Shared helpers used by more than one node — kept out of agent/graph.py
so each node module stays a thin, single-purpose function."""
import os
from typing import Any

from components.c09_working_memory.src.working_memory import resolve_ref
from tools import workspace
from tools.registry import get_tool


def peek_current_value(step: dict[str, Any]) -> Any:
    """Best-effort read of a write/create step's current target state, so
    the policy engine can tell an overwrite from a write-to-empty (or a
    create-over-an-existing-file from a genuinely new one). Returns None on
    any failure (missing file, unknown target, etc.) — the safer default
    (reversible-write-empty / create-new-file) rather than blocking on a
    step that hasn't been created yet.

    "create" steps don't have a read op to call (there's nothing to read
    yet) — file existence at the resolved workspace path stands in for
    "does the target already have content" instead.
    """
    target = step.get("target") or {}

    if step.get("type") == "create":
        file_name = target.get("file")
        if not file_name:
            return None
        resolved_path = workspace.resolve(file_name)
        return resolved_path if os.path.exists(resolved_path) else None

    try:
        tool = get_tool(target.get("app"))
    except LookupError:
        return None
    try:
        result = tool.run({**step, "type": "read"})
    except Exception:  # noqa: BLE001 - deliberately broad: any read failure means "unknown"
        return None
    return result.get("value")


def resolve_step_value(task_id: str, step: dict[str, Any]) -> Any:
    ref = step.get("value_ref") or (step.get("target") or {}).get("value_ref")
    if ref:
        resolved = resolve_ref(task_id, ref)
        if resolved is not None:
            return resolved
    if step.get("value") is not None:
        return step["value"]
    return (step.get("target") or {}).get("value")
