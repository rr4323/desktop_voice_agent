"""Builds the agent's LangGraph StateGraph — the orchestration layer that
replaces the never-built c13_orchestrator (see that component's own
`src/orchestrator.py`, now a thin wrapper around get_graph() here).

Node/edge shape mirrors the TDD §5.1 data flow:

    START -> transcribe -> plan
    plan --no steps / single clarify step--> respond
    plan --otherwise--> policy_check
    policy_check --ALLOW--------> execute
    policy_check --ASK_CONFIRM--> confirm
    policy_check --DENY---------> deny
    confirm --confirmed--> execute
    confirm --declined---> cancel
    execute -> verify -> audit
    deny -> audit
    cancel -> audit
    audit --more steps--> policy_check
    audit --done--------> respond -> END

`confirm` pauses the whole graph via LangGraph's `interrupt()` (see
agent/nodes/confirm.py) — the checkpointer is what makes that pause
survive across the server's own request/response boundary; resuming later
with `Command(resume=...)` on the same thread_id picks up exactly where
the graph left off, no hand-rolled pause/resume bookkeeping needed.
"""
import os
import sqlite3
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from agent.nodes.audit import audit
from agent.nodes.cancel import cancel
from agent.nodes.confirm import confirm
from agent.nodes.deny import deny
from agent.nodes.execute import execute
from agent.nodes.plan import plan
from agent.nodes.policy_check import policy_check
from agent.nodes.respond import respond
from agent.nodes.transcribe import transcribe
from agent.nodes.verify import verify
from agent.state import AgentState


def _route_after_plan(state: dict[str, Any]) -> str:
    steps = state["plan"]["steps"]
    # The planner's system prompt asks for a *lone* clarify step when
    # ambiguous, but nothing stops a model from mixing one in alongside
    # real action steps anyway — and executing some steps before
    # discovering a clarify step further down the plan would both do
    # something the user didn't unambiguously ask for *and* crash
    # execute_node (a clarify target has no "app" to dispatch on). So: any
    # clarify step anywhere in the plan means stop and ask before running
    # anything, not just when it's the plan's only step.
    if not steps or any(step["type"] == "clarify" for step in steps):
        return "respond"
    return "policy_check"


def _route_after_policy(state: dict[str, Any]) -> str:
    decision = state["current_decision"]["decision"]
    if decision == "ALLOW":
        return "execute"
    if decision == "ASK_CONFIRM":
        return "confirm"
    return "deny"


def _route_after_confirm(state: dict[str, Any]) -> str:
    print(9)
    return "execute" if state.get("confirmed") else "cancel"


def _route_after_audit(state: dict[str, Any]) -> str:
    return "respond" if state.get("done") else "policy_check"


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    graph = StateGraph(AgentState)

    graph.add_node("transcribe", transcribe)
    graph.add_node("plan", plan)
    graph.add_node("policy_check", policy_check)
    graph.add_node("confirm", confirm)
    graph.add_node("execute", execute)
    graph.add_node("verify", verify)
    graph.add_node("deny", deny)
    graph.add_node("cancel", cancel)
    graph.add_node("audit", audit)
    graph.add_node("respond", respond)

    graph.add_edge(START, "transcribe")
    graph.add_edge("transcribe", "plan")
    graph.add_conditional_edges("plan", _route_after_plan, ["policy_check", "respond"])
    graph.add_conditional_edges("policy_check", _route_after_policy, ["execute", "confirm", "deny"])
    graph.add_conditional_edges("confirm", _route_after_confirm, ["execute", "cancel"])
    graph.add_edge("execute", "verify")
    graph.add_edge("verify", "audit")
    graph.add_edge("deny", "audit")
    graph.add_edge("cancel", "audit")
    graph.add_conditional_edges("audit", _route_after_audit, ["policy_check", "respond"])
    graph.add_edge("respond", END)

    return graph.compile(checkpointer=checkpointer or InMemorySaver())


_graph = None
_checkpoint_conn: sqlite3.Connection | None = None


def _persistent_checkpointer() -> SqliteSaver:
    """File-backed checkpointer for the server's process-wide graph.

    A pending ASK_CONFIRM/clarify task pauses via interrupt() (see
    agent/nodes/confirm.py) relying on the checkpointer to hold that
    task's state until the matching Command(resume=...) arrives on a
    later turn. With the previous InMemorySaver, a process restart in
    between (e.g. `uvicorn --reload` picking up an unrelated file change)
    silently drops that state — the resume then has no checkpoint to
    resume, and server/sessions.py's own persistence (see save()) is what
    lets the *next* incoming message even know a resume was expected.
    SqliteSaver's own docstring: safe to share across threads via its
    internal lock despite check_same_thread=False, which is what
    asyncio.to_thread(graph.invoke, ...) in server/ws.py needs.
    """
    global _checkpoint_conn
    if _checkpoint_conn is None:
        db_path = os.environ.get("AGENT_CHECKPOINT_DB", "data/agent_checkpoints.sqlite")
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        _checkpoint_conn = sqlite3.connect(db_path, check_same_thread=False)
        # See server/sessions.py's identical PRAGMA for why: without a
        # busy_timeout, a lock briefly held by another connection on this
        # file (another process pointed at this repo, a concurrent
        # to_thread(graph.invoke) call) fails immediately instead of
        # waiting for it to clear.
        _checkpoint_conn.execute("PRAGMA busy_timeout = 5000")
    saver = SqliteSaver(_checkpoint_conn)
    saver.setup()
    return saver


def get_graph():
    """Process-wide singleton compiled graph, for the server. Tests that
    want an isolated checkpointer should call build_graph() directly
    instead."""
    global _graph
    if _graph is None:
        _graph = build_graph(checkpointer=_persistent_checkpointer())
    return _graph
