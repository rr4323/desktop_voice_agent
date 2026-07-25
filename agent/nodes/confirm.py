"""Confirmation loop node (TDD §5.1): pauses the graph via LangGraph's
`interrupt()` and surfaces a prompt for the server to relay to the user;
resumes with whatever the client sends back on the next turn, parsed
deterministically by component 02 (never an LLM call — see that
component's own docstring on why)."""
from typing import Any

from langgraph.types import interrupt

from components.c02_confirmation_parser.src.confirmation_parser import parse_confirmation

# Cap on re-asking after an ambiguous ("needs_reprompt") reply, so a client
# that can never produce a clear yes/no doesn't hang the task forever — it
# falls back to the safe default (declined) instead of guessing.
_MAX_REPROMPTS = 2


def _confirm_prompt(step: dict[str, Any], decision: dict[str, Any]) -> str:
    target = step.get("target", {})
    field = target.get("cell") or target.get("placeholder") or target.get("element_name") or target.get("instruction") or "this"
    return f"{decision['reason']} — should I proceed with {field}?"


def confirm(state: dict[str, Any]) -> dict[str, Any]:
    # Deliberately sync, not async: langgraph's interrupt() reads a
    # contextvar that isn't reliably propagated into an async node's task
    # on Python < 3.11 (raises "Called get_config outside of a runnable
    # context"). A sync node has no such caveat, and nothing else in this
    # node is slow enough to need asyncio.to_thread anyway.
    step = state["current_step"]
    decision = state["current_decision"]
    prompt = _confirm_prompt(step, decision)
    print(4)
    print(prompt)
    for _attempt in range(_MAX_REPROMPTS + 1):
        print(5)
        reply_transcript = interrupt({"prompt": prompt, "step_id": step["step_id"]})
        print(reply_transcript)
        parsed = parse_confirmation({"transcript": reply_transcript})
        print("parsed")
        print(parsed)
        if not parsed.get("needs_reprompt"):
            return {"confirmed": parsed["confirmed"], "pending_confirmation": None}
        prompt = f"Sorry, I didn't catch a clear yes or no — {_confirm_prompt(step, decision)}"

    return {"confirmed": False, "pending_confirmation": None}
