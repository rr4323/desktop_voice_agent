"""Orchestrator (component 13): wires every other component together per
the TDD data flow. Contract: docs/Component_IO_Spec.md, section 13.

Historically the "build last" integration component, and the one that
stayed a stub the longest in this repo. The real orchestration logic now
lives in agent/graph.py — a LangGraph StateGraph built specifically to add
what a hand-rolled orchestrator function couldn't: human-in-the-loop
pausing for ASK_CONFIRM via LangGraph's own interrupt()/checkpointer,
text-or-audio input/output, and a FastAPI/WebSocket front end (see
server/). This function is a thin, non-interactive synchronous wrapper
around that graph, kept so this component's own directory/tests stay
meaningful as the "run the whole pipeline end-to-end" entry point the IO
spec describes — auto-resolving any ASK_CONFIRM prompts instead of
pausing for a real user, since there's no interactive channel at this
call boundary (that's what server/ws.py is for).
"""
import uuid
from typing import Any

from langgraph.types import Command

from agent.graph import get_graph


def run_task(request: dict[str, Any]) -> dict[str, Any]:
    """request: {"transcript": str, "context"?: dict, "task_id"?: str,
    "auto_confirm"?: bool (default True), "confirm_replies"?: [str, ...]}

    Any ASK_CONFIRM interrupt is resolved automatically: from
    "confirm_replies" in order if given, else a blanket "yes go ahead" (or
    "no, cancel that" if auto_confirm=False) for every confirmation the
    plan raises.
    """
    transcript = request.get("transcript", "")
    context = request.get("context") or {"open_files": [], "working_memory": {}}
    auto_confirm = request.get("auto_confirm", True)
    confirm_replies = list(request.get("confirm_replies") or [])

    task_id = request.get("task_id") or f"task_{uuid.uuid4().hex[:8]}"
    graph = get_graph()
    config = {"configurable": {"thread_id": task_id}}

    result = graph.invoke(
        {
            "session_id": task_id,
            "task_id": task_id,
            "input_mode": "text",
            "transcript": transcript,
            "context": context,
        },
        config=config,
    )

    while "__interrupt__" in result:
        reply = confirm_replies.pop(0) if confirm_replies else ("yes go ahead" if auto_confirm else "no, cancel that")
        result = graph.invoke(Command(resume=reply), config=config)

    status = "done"
    results = result.get("results", [])
    if results:
        last = results[-1]
        if last["decision"]["decision"] == "DENY":
            status = "denied"
        elif last["result"].get("error") == "cancelled_by_user":
            status = "cancelled"

    audit_trail = [
        f"step {r['step']['step_id']}: {r['decision']['decision']} -> "
        f"{'success' if r['result'].get('success', True) else 'failed'}"
        for r in results
    ]

    return {
        "task_id": task_id,
        "status": status,
        "audit_trail": audit_trail,
        "final_text": result.get("final_text"),
        "results": results,
    }
