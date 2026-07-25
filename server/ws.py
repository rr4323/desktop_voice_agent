"""WebSocket endpoint: turn-based text/audio in, text/audio out.

Protocol
--------
Client -> server (one JSON object per turn):
    {"type": "text", "text": "...", "context"?: {...}}
    {"type": "audio", "audio_b64": "...", "mime"?: "audio/wav", "context"?: {...}}
    {"type": "cancel"}

Server -> client:
    {"type": "status", "stage": "planning"}
    {"type": "confirm_request", "prompt": "...", "step_id": N}
    {"type": "final", "text": "...", "audio_b64": "..."|null, "task_id": "...", "results": [...]}
    {"type": "error", "message": "..."}

Each turn either starts a new task or resumes one paused on a pending
ASK_CONFIRM (agent/nodes/confirm.py's interrupt()). Blocking graph work
runs via asyncio.to_thread so one session's long task doesn't stall the
event loop for other connections.
"""
import asyncio
import base64
import os
import tempfile
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langgraph.types import Command

from agent import tracing
from agent.graph import get_graph
from components.c01_asr.src.asr import transcribe as asr_transcribe
from server.schemas import ClientAudioMessage, ClientCancelMessage, parse_client_message
from server.sessions import Session, drop, get_or_create, record_message, save

router = APIRouter()

_DEFAULT_CONTEXT = {"open_files": [], "working_memory": {}}


def _decode_audio_to_tempfile(audio_b64: str) -> str:
    raw = base64.b64decode(audio_b64)
    fd, path = tempfile.mkstemp(suffix=".wav")
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    return path


async def _run_graph(payload_or_command: Any, task_id: str) -> dict[str, Any]:
    graph = get_graph()
    config = {"configurable": {"thread_id": task_id}, "callbacks": tracing.callbacks()}
    return await asyncio.to_thread(graph.invoke, payload_or_command, config=config)


def _confirm_event(result: dict[str, Any]) -> dict[str, Any]:
    payload = result["__interrupt__"][0].value
    return {"type": "confirm_request", "prompt": payload["prompt"], "step_id": payload["step_id"]}


def _final_event(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "final",
        "text": result.get("final_text"),
        "audio_b64": result.get("final_audio_b64"),
        "task_id": result.get("task_id"),
        "results": [
            {
                "step_id": r["step"]["step_id"],
                "decision": r["decision"]["decision"],
                "success": r["result"].get("success", True),
                "verified": r["verification"].get("postcondition_met"),
            }
            for r in result.get("results", [])
        ],
    }


def _is_clarify_result(result: dict[str, Any]) -> bool:
    steps = (result.get("plan") or {}).get("steps") or []
    return any(s.get("type") == "clarify" for s in steps)


async def _send(websocket: WebSocket, session: Session, payload: dict[str, Any]) -> None:
    """Send one server->client event and, unless it's just a progress
    ping ("status"), append it to conversation_history as the assistant's
    turn (see server/sessions.py's record_message)."""
    await websocket.send_json(payload)
    if payload.get("type") == "status":
        return
    text = payload.get("text") or payload.get("prompt") or payload.get("message")
    record_message(session.session_id, session.current_task_id, "assistant", payload["type"], text)


async def _extract_text(message: Any) -> str:
    if isinstance(message, ClientAudioMessage):
        audio_path = _decode_audio_to_tempfile(message.audio_b64)
        transcribed = await asyncio.to_thread(asr_transcribe, {"audio_path": audio_path})
        return transcribed["transcript"]
    return message.text


async def _handle_clarify_continuation(websocket: WebSocket, session: Session, message: Any) -> dict[str, Any]:
    reply_text = await _extract_text(message)
    combined_transcript = (
        f'{session.pending_transcript}\n'
        f'Assistant asked: "{session.pending_question}"\n'
        f"User: {reply_text}"
    )
    session.awaiting_clarification = False

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    session.current_task_id = task_id
    initial_state = {
        "session_id": session.session_id,
        "task_id": task_id,
        "input_mode": "text",
        "transcript": combined_transcript,
        "context": _DEFAULT_CONTEXT,
    }
    await _send(websocket, session, {"type": "status", "stage": "planning"})
    return await _run_graph(initial_state, task_id)


async def _handle_new_task(websocket: WebSocket, session: Session, message: Any) -> dict[str, Any]:
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    session.current_task_id = task_id
    context = getattr(message, "context", None) or _DEFAULT_CONTEXT

    if isinstance(message, ClientAudioMessage):
        session.input_mode = "audio"
        initial_state = {
            "session_id": session.session_id,
            "task_id": task_id,
            "input_mode": "audio",
            "audio_path": _decode_audio_to_tempfile(message.audio_b64),
            "transcript": "",
            "context": context,
        }
    else:
        session.input_mode = "text"
        initial_state = {
            "session_id": session.session_id,
            "task_id": task_id,
            "input_mode": "text",
            "transcript": message.text,
            "context": context,
        }

    await _send(websocket, session, {"type": "status", "stage": "planning"})
    return await _run_graph(initial_state, task_id)


async def _handle_confirmation_reply(message: Any, reply_override: str | None = None) -> str:
    if reply_override is not None:
        return reply_override
    return await _extract_text(message)


def _confirmation_actually_pending(session: Session) -> bool:
    """True only if the graph's own checkpoint still has a paused
    interrupt to resume for session.current_task_id, not just if the
    session *thinks* one is pending.

    server/sessions.py's awaiting_confirmation flag and agent/graph.py's
    checkpointer are two independently persisted stores (data/sessions.sqlite
    vs. data/agent_checkpoints.sqlite) updated by different code paths —
    they're kept in sync today, but nothing enforces that, so this treats
    the checkpoint as the source of truth before ever building a
    Command(resume=...) call against it. On a mismatch, clears the stale
    session flags (so the caller falls through to starting a fresh task
    instead of resuming a thread with nothing to resume) and persists
    that correction.
    """
    if not (session.awaiting_confirmation and session.current_task_id):
        return False
    graph = get_graph()
    config = {"configurable": {"thread_id": session.current_task_id}}
    snapshot = graph.get_state(config)
    if any(task.interrupts for task in snapshot.tasks):
        return True
    session.awaiting_confirmation = False
    session.awaiting_clarification = False
    save(session.session_id)
    return False


@router.websocket("/ws/agent/{session_id}")
async def agent_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    session = get_or_create(session_id)

    try:
        while True:
            raw = await websocket.receive_json()
            try:
                message = parse_client_message(raw)
            except Exception as exc:  # noqa: BLE001 - malformed client input, not a server fault
                await _send(websocket, session, {"type": "error", "message": str(exc)})
                continue

            if isinstance(message, ClientAudioMessage):
                record_message(session_id, session.current_task_id, "user", "audio", None)
            elif isinstance(message, ClientCancelMessage):
                record_message(session_id, session.current_task_id, "user", "cancel", None)
            else:
                record_message(session_id, session.current_task_id, "user", "text", message.text)

            if isinstance(message, ClientCancelMessage):
                if _confirmation_actually_pending(session):
                    try:
                        result = await _run_graph(Command(resume="cancel"), session.current_task_id)
                    except Exception as exc:  # noqa: BLE001 - see the matching except below
                        session.awaiting_confirmation = False
                        session.awaiting_clarification = False
                        save(session_id)
                        await _send(websocket, session, {"type": "error", "message": str(exc)})
                        continue
                    session.awaiting_confirmation = False
                    session.awaiting_clarification = False
                    save(session_id)
                    await _send(websocket, session, _final_event(result))
                    continue
                elif session.awaiting_clarification:
                    session.awaiting_clarification = False
                    session.pending_transcript = ""
                    session.pending_question = ""
                    save(session_id)
                    await _send(
                        websocket,
                        session,
                        {"type": "final", "text": "Okay, cancelled.", "task_id": session.current_task_id, "results": []},
                    )
                    continue
                else:
                    await _send(websocket, session, {"type": "error", "message": "nothing to cancel"})
                    continue

            try:
                if _confirmation_actually_pending(session):
                    reply_text = await _handle_confirmation_reply(message)
                    result = await _run_graph(Command(resume=reply_text), session.current_task_id)

                elif session.awaiting_clarification and session.current_task_id:
                    result = await _handle_clarify_continuation(websocket, session, message)

                else:
                    result = await _handle_new_task(websocket, session, message)
                if "__interrupt__" in result:
                    session.awaiting_confirmation = True
                    session.awaiting_clarification = False
                    save(session_id)

                    await _send(websocket, session, _confirm_event(result))
                elif _is_clarify_result(result):
                    session.awaiting_confirmation = False
                    session.awaiting_clarification = True
                    session.pending_transcript = result.get("transcript", "")
                    session.pending_question = result.get("final_text", "")
                    save(session_id)
                    await _send(websocket, session, _final_event(result))
                else:
                    session.awaiting_confirmation = False
                    session.awaiting_clarification = False
                    save(session_id)
                    await _send(websocket, session, _final_event(result))
            except Exception as exc:  # noqa: BLE001 - a mid-task failure must not leave
                # this session's `_sessions` entry (module-global, outlives this
                # connection) permanently stuck awaiting a confirmation/clarification
                # the client never received and can't answer.
                session.awaiting_confirmation = False
                session.awaiting_clarification = False
                save(session_id)
                await _send(websocket, session, {"type": "error", "message": str(exc)})

    except WebSocketDisconnect:
        drop(session_id)
