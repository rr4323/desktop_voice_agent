"""Standalone tests for the Task Planner (LLM) (component 04).

Run in isolation: pytest components/c04_planner

The Groq network call (`_call_groq`) is mocked for all but the final
opt-in live smoke test, so this suite runs without a live GROQ_API_KEY —
same "skip cleanly if unreachable" spirit as c17_browser_agent's tests.
"""
import json

import pytest
import requests

from components.c04_planner.src import planner
from components.c04_planner.src.planner import plan


def test_clear_request_produces_schema_valid_two_step_plan(monkeypatch):
    mock_response = {
        "goal": "Copy Q3 revenue total from network_report.pdf into kpi_tracker.xlsx",
        "steps": [
            {
                "step_id": 1,
                "type": "read",
                "target": {"app": "pdf", "file": "network_report.pdf", "query": "Q3 revenue total"},
                "value_ref": None,
                "depends_on": [],
            },
            {
                "step_id": 2,
                "type": "write",
                "target": {"app": "xlsx", "file": "kpi_tracker.xlsx", "cell": "B7"},
                "value_ref": "step_1.value",
                "depends_on": [1],
            },
        ],
    }
    monkeypatch.setattr(planner, "_call_groq", lambda *_: json.dumps(mock_response))

    result = plan(
        {
            "transcript": "pull the q3 revenue total from the network report and put it into the kpi tracker",
            "context": {"open_files": ["network_report.pdf", "kpi_tracker.xlsx"], "working_memory": {}},
        }
    )

    assert result == mock_response


def test_empty_transcript_emits_clarify_without_calling_model(monkeypatch):
    called = []
    monkeypatch.setattr(planner, "_call_groq", lambda *_: called.append(1) or "{}")

    result = plan({"transcript": "", "context": {"open_files": []}})

    assert not called
    assert result["steps"][0]["type"] == "clarify"


def test_ambiguous_request_emits_single_clarify_step(monkeypatch):
    mock_response = {
        "goal": "Clarify which deck to update",
        "steps": [
            {
                "step_id": 1,
                "type": "clarify",
                "target": {"question": "Two decks are open — which one should I update?"},
                "value_ref": None,
                "depends_on": [],
            }
        ],
    }
    monkeypatch.setattr(planner, "_call_groq", lambda *_: json.dumps(mock_response))

    result = plan(
        {
            "transcript": "update the deck",
            "context": {"open_files": ["exec_briefing.pptx", "board_review.pptx"], "working_memory": {}},
        }
    )

    assert len(result["steps"]) == 1
    assert result["steps"][0]["type"] == "clarify"


def test_invalid_json_retries_then_falls_back_to_clarify(monkeypatch):
    calls = {"count": 0}

    def flaky_call(*_args):
        calls["count"] += 1
        return "not json at all"

    monkeypatch.setattr(planner, "_call_groq", flaky_call)

    result = plan({"transcript": "do something", "context": {"open_files": []}})

    assert calls["count"] == planner._MAX_ATTEMPTS
    assert result["steps"][0]["type"] == "clarify"


def test_schema_invalid_response_falls_back_to_clarify(monkeypatch):
    # Missing required "target" key on the step.
    bad_response = {"goal": "g", "steps": [{"step_id": 1, "type": "read"}]}
    monkeypatch.setattr(planner, "_call_groq", lambda *_: json.dumps(bad_response))

    result = plan({"transcript": "do something", "context": {"open_files": []}})

    assert result["steps"][0]["type"] == "clarify"


def test_network_error_falls_back_to_clarify(monkeypatch):
    def raise_connection_error(*_args):
        raise requests.ConnectionError("no route to host")

    monkeypatch.setattr(planner, "_call_groq", raise_connection_error)

    result = plan({"transcript": "do something", "context": {"open_files": []}})

    assert result["steps"][0]["type"] == "clarify"


def test_missing_api_key_falls_back_to_clarify_without_network_call(monkeypatch):
    monkeypatch.setattr(planner, "_GROQ_API_KEY", None)

    result = plan({"transcript": "do something", "context": {"open_files": []}})

    assert result["steps"][0]["type"] == "clarify"


def test_live_groq_smoke():
    """Opt-in: only runs meaningfully with a live GROQ_API_KEY set. Skips
    cleanly otherwise rather than failing CI."""
    if not planner._GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY not set; skipping live smoke test")

    result = plan(
        {
            "transcript": "pull the q3 revenue total from the network report and put it into the kpi tracker",
            "context": {"open_files": ["network_report.pdf", "kpi_tracker.xlsx"], "working_memory": {}},
        }
    )
    assert "goal" in result
    assert isinstance(result["steps"], list)
