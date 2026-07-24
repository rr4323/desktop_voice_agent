"""Track in-flight tasks so prompts can be changed or cancelled midway."""
import json
import os
import uuid
from datetime import datetime, timezone


def _sessions_dir(base_dir: str) -> str:
    path = os.path.join(base_dir, ".sessions")
    os.makedirs(path, exist_ok=True)
    return path


def create_session(base_dir: str, prompt: str, files: list[str], intent: dict) -> str:
    session_id = uuid.uuid4().hex[:8]
    payload = {
        "id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "prompt": prompt,
        "files": files,
        "intent": intent,
        "history": [{"prompt": prompt, "intent": intent}],
    }
    _save(base_dir, session_id, payload)
    return session_id


def load_session(base_dir: str, session_id: str) -> dict | None:
    path = os.path.join(_sessions_dir(base_dir), f"{session_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def update_session(base_dir: str, session_id: str, prompt: str, intent: dict, files: list[str] | None = None) -> dict:
    session = load_session(base_dir, session_id)
    if session is None:
        raise ValueError(f"Session not found: {session_id}")
    session["prompt"] = prompt
    session["intent"] = intent
    if files is not None:
        session["files"] = files
    session["history"].append({"prompt": prompt, "intent": intent})
    _save(base_dir, session_id, session)
    return session


def cancel_session(base_dir: str, session_id: str, reason: str = "User cancelled the task.") -> dict:
    session = load_session(base_dir, session_id)
    if session is None:
        raise ValueError(f"Session not found: {session_id}")
    session["status"] = "cancelled"
    session["cancel_reason"] = reason
    _save(base_dir, session_id, session)
    return session


def complete_session(base_dir: str, session_id: str, result: dict) -> dict:
    session = load_session(base_dir, session_id)
    if session is None:
        raise ValueError(f"Session not found: {session_id}")
    session["status"] = "done"
    session["result"] = result
    _save(base_dir, session_id, session)
    return session


def _save(base_dir: str, session_id: str, payload: dict) -> None:
    path = os.path.join(_sessions_dir(base_dir), f"{session_id}.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
