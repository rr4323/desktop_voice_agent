"""State Manager (component 11): task graph tracking step status across a
task; supports pause, resume, correction, cancellation.

Contract: docs/Component_IO_Spec.md, section 11.

Ported from the working prototype in part4/state_manager.py (a `TaskGraph`
class holding one task's steps + rollback callables), reshaped into this
component's documented single-dict-in/single-dict-out `apply_operation`
entry point and re-keyed by `task_id` so one process can track many
concurrent tasks (one per voice session) rather than just one.

Rollback callables aren't part of this component's documented contract
(they can't survive a dict-shaped request/response boundary or a JSON
reload) — TDD §6.6's rollback-on-cancel is instead handled by the
`ASK_CONFIRM` gate happening *before* any write executes, which is the
primary safety mechanism per TDD §4.
"""
import json
import os
from typing import Any

_VALID_STATUSES = {"pending", "in_progress", "done", "failed", "paused"}
_DEFAULT_TASK_ID = "default"

# Optional on-disk persistence so a killed/restarted process can reload and
# resume without re-executing completed steps (IO spec §11's standalone
# test explicitly calls this out). Off by default; set via env var or pass
# "storage_path" in a request to opt in.
_STORAGE_PATH = os.environ.get("STATE_MANAGER_STORAGE_PATH")

# task_id -> step_id -> {"status": ..., "meta": {...}}
_tasks: dict[str, dict[str, dict[str, Any]]] = {}


def _storage_path(request: dict[str, Any]) -> str | None:
    return request.get("storage_path") or _STORAGE_PATH


def _load(path: str) -> None:
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        _tasks.update(data.get("tasks", {}))
    except (OSError, json.JSONDecodeError):
        pass


def _save(path: str | None) -> None:
    if not path:
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"tasks": _tasks}, f, indent=2)


def _view(task_id: str) -> dict[str, Any]:
    steps = _tasks.get(task_id, {})
    return {
        "task_id": task_id,
        "steps": [
            {"step_id": int(sid) if sid.isdigit() else sid, "status": s["status"]}
            for sid, s in steps.items()
        ],
    }


def apply_operation(request: dict[str, Any]) -> dict[str, Any]:
    """Apply one task-graph operation and return the resulting step view.

    request: {"operation", "task_id"?, "step_id"?, "status"?, "meta"?,
              "new_target"?, "storage_path"?}
    operations: add_step, update_status, pause, resume, correct, cancel, get
    """
    path = _storage_path(request)
    if path:
        _load(path)

    operation = request.get("operation")
    task_id = request.get("task_id") or _DEFAULT_TASK_ID
    steps = _tasks.setdefault(task_id, {})

    if operation == "add_step":
        step_id = str(request["step_id"])
        steps[step_id] = {"status": "pending", "meta": request.get("meta") or {}}

    elif operation == "update_status":
        step_id = str(request["step_id"])
        status = request["status"]
        if status not in _VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {_VALID_STATUSES}")
        steps.setdefault(step_id, {"status": "pending", "meta": {}})["status"] = status

    elif operation == "pause":
        target_ids = [str(request["step_id"])] if request.get("step_id") is not None else list(steps)
        for sid in target_ids:
            if sid in steps and steps[sid]["status"] in ("pending", "in_progress"):
                steps[sid]["status"] = "paused"

    elif operation == "resume":
        target_ids = [str(request["step_id"])] if request.get("step_id") is not None else list(steps)
        for sid in target_ids:
            if sid in steps and steps[sid]["status"] == "paused":
                steps[sid]["status"] = "in_progress"

    elif operation == "correct":
        step_id = str(request["step_id"])
        if step_id not in steps:
            raise KeyError(f"Step {step_id} not found in task {task_id}.")
        if request.get("new_target") is not None:
            steps[step_id]["meta"]["target"] = request["new_target"]
        steps[step_id]["status"] = "pending"

    elif operation == "cancel":
        for s in steps.values():
            if s["status"] in ("pending", "in_progress", "paused"):
                s["status"] = "failed"

    elif operation == "get":
        pass

    else:
        raise ValueError(f"Unknown operation '{operation}'")

    _save(path)
    return _view(task_id)
