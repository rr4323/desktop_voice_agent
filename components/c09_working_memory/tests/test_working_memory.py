"""Standalone tests for the Working Memory Store (component 09).

Run in isolation: pytest components/c09_working_memory
"""
from components.c09_working_memory.src.working_memory import get_provenance, resolve_ref, set_or_get


def test_set_then_get_round_trips_value_and_provenance():
    set_or_get(
        {
            "operation": "set",
            "task_id": "t1",
            "key": "step_1.value",
            "value": "2.4M",
            "provenance": {"file": "network_report.pdf", "page": 3},
        }
    )
    result = set_or_get({"operation": "get", "task_id": "t1", "key": "step_1.value"})
    assert result == {
        "key": "step_1.value",
        "value": "2.4M",
        "provenance": {"file": "network_report.pdf", "page": 3},
    }


def test_get_missing_key_returns_none_value():
    result = set_or_get({"operation": "get", "task_id": "t1", "key": "does_not_exist"})
    assert result["value"] is None
    assert result["provenance"] == {}


def test_clear_removes_task_scope():
    set_or_get({"operation": "set", "task_id": "t2", "key": "step_1.value", "value": "42"})
    set_or_get({"operation": "clear", "task_id": "t2"})
    result = set_or_get({"operation": "get", "task_id": "t2", "key": "step_1.value"})
    assert result["value"] is None


def test_tasks_are_isolated_from_each_other():
    set_or_get({"operation": "set", "task_id": "task_a", "key": "step_1.value", "value": "A"})
    set_or_get({"operation": "set", "task_id": "task_b", "key": "step_1.value", "value": "B"})
    assert set_or_get({"operation": "get", "task_id": "task_a", "key": "step_1.value"})["value"] == "A"
    assert set_or_get({"operation": "get", "task_id": "task_b", "key": "step_1.value"})["value"] == "B"


def test_resolve_ref_resolves_a_known_key():
    set_or_get({"operation": "set", "task_id": "t3", "key": "step_1.value", "value": "2.4M"})
    assert resolve_ref("t3", "step_1.value") == "2.4M"


def test_resolve_ref_passes_through_literal_values():
    assert resolve_ref("t3", "2.4M") == "2.4M"
    assert resolve_ref("t3", 42) == 42


def test_get_provenance_helper():
    set_or_get(
        {
            "operation": "set",
            "task_id": "t4",
            "key": "step_1.value",
            "value": "2.4M",
            "provenance": {"file": "report.pdf", "page": 3},
        }
    )
    assert get_provenance("t4", "step_1.value") == {"file": "report.pdf", "page": 3}
    assert get_provenance("t4", "missing") is None
