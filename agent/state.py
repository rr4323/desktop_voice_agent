"""LangGraph state for the unified agent.

Drives the TDD §5.1 pipeline (ASR -> Plan -> Policy -> Confirm -> Execute
-> Verify -> Audit -> Respond) as one StateGraph per task. One `thread_id`
(== session_id, see server/sessions.py) persists this state across the
`interrupt()`/resume cycle a mid-task ASK_CONFIRM causes.
"""
import operator
from typing import Annotated, Any, Literal, TypedDict


class AgentState(TypedDict, total=False):
    session_id: str
    task_id: str

    input_mode: Literal["text", "audio"]
    audio_path: str | None  # temp .wav path, set by the server for audio turns
    transcript: str
    context: dict[str, Any]  # {"open_files": [...], "working_memory": {...}}

    plan: dict[str, Any] | None  # {"goal": str, "steps": [ActionRequest, ...]}
    step_index: int
    current_step: dict[str, Any] | None
    current_decision: dict[str, Any] | None  # PolicyDecision

    pending_confirmation: dict[str, Any] | None  # {"prompt": str, "step_id": int}
    confirmed: bool | None

    execute_result: dict[str, Any] | None  # ActionResult-shaped
    verification: dict[str, Any] | None
    terminate_task: bool  # set by deny/cancel nodes to stop the step loop early

    # One entry per finished step; Annotated with operator.add so each
    # audit-node return accumulates rather than overwrites across the loop.
    results: Annotated[list[dict[str, Any]], operator.add]

    final_text: str | None
    final_audio_b64: str | None
    done: bool
