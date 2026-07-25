"""Standalone tests for the State Manager (component 11).

Run in isolation: pytest components/c11_state_manager
"""
import json
import os

from components.c11_state_manager.src.state_manager import apply_operation


def test_add_step_then_update_status():
    apply_operation({"operation": "add_step", "task_id": "t1", "step_id": 1})
    result = apply_operation({"operation": "update_status", "task_id": "t1", "step_id": 2, "status": "done"})
    assert result["task_id"] == "t1"
    statuses = {s["step_id"]: s["status"] for s in result["steps"]}
    assert statuses[1] == "pending"
    assert statuses[2] == "done"


def test_scripted_sequence_start_pause_resume_correct_cancel():
    task_id = "t_scripted"
    apply_operation({"operation": "add_step", "task_id": task_id, "step_id": 1})
    apply_operation({"operation": "update_status", "task_id": task_id, "step_id": 1, "status": "in_progress"})

    paused = apply_operation({"operation": "pause", "task_id": task_id, "step_id": 1})
    assert {s["step_id"]: s["status"] for s in paused["steps"]}[1] == "paused"

    resumed = apply_operation({"operation": "resume", "task_id": task_id, "step_id": 1})
    assert {s["step_id"]: s["status"] for s in resumed["steps"]}[1] == "in_progress"

    corrected = apply_operation(
        {"operation": "correct", "task_id": task_id, "step_id": 1, "new_target": {"cell": "C7"}}
    )
    assert {s["step_id"]: s["status"] for s in corrected["steps"]}[1] == "pending"

    apply_operation({"operation": "add_step", "task_id": task_id, "step_id": 2})
    cancelled = apply_operation({"operation": "cancel", "task_id": task_id})
    assert all(s["status"] == "failed" for s in cancelled["steps"])


def test_invalid_status_raises():
    import pytest

    with pytest.raises(ValueError):
        apply_operation({"operation": "update_status", "task_id": "t2", "step_id": 1, "status": "bogus"})


def test_tasks_are_isolated():
    apply_operation({"operation": "add_step", "task_id": "task_a", "step_id": 1})
    apply_operation({"operation": "update_status", "task_id": "task_a", "step_id": 1, "status": "done"})
    result_b = apply_operation({"operation": "get", "task_id": "task_b"})
    assert result_b["steps"] == []


def test_resume_from_last_completed_step_after_reload(tmp_path):
    # Kill-and-reload path: persist to disk, then read back via a fresh
    # operation using the same storage_path, and confirm the previously
    # completed step is still marked done (not silently reset/re-executed).
    storage_path = str(tmp_path / "state.json")
    task_id = "t_reload"
    apply_operation({"operation": "add_step", "task_id": task_id, "step_id": 1, "storage_path": storage_path})
    apply_operation(
        {"operation": "update_status", "task_id": task_id, "step_id": 1, "status": "done", "storage_path": storage_path}
    )
    assert os.path.exists(storage_path)
    with open(storage_path) as f:
        on_disk = json.load(f)
    assert on_disk["tasks"][task_id]["1"]["status"] == "done"

    result = apply_operation({"operation": "get", "task_id": task_id, "storage_path": storage_path})
    assert {s["step_id"]: s["status"] for s in result["steps"]}[1] == "done"
