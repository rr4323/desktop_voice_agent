"""Per-connection session bookkeeping + conversation history.

Deliberately thin on the routing side — the actual task state (plan,
step_index, results, ...) lives in the graph's own checkpointer, keyed by
thread_id. Session just tracks what's needed to route the *next* incoming
websocket message: whether we're mid-confirmation, which task that
confirmation belongs to, and what modality to respond in.

thread_id is scoped to one *task*, not the whole websocket connection —
minted fresh each time a new task starts, reused only for the
confirm/resume cycle within that task. Reusing the session_id itself as
thread_id across multiple unrelated tasks over a long-lived connection
would leak state between them (e.g. `results` in agent/state.py is
accumulated with an operator.add reducer, so an old task's results would
never clear).

Both tables live in a dedicated SQLite file (data/sessions.sqlite),
separate from agent/graph.py's own checkpoint database — different
subsystems, different owners, same "why this survives a restart" reason:
a server restart mid-task (e.g. `uvicorn --reload` on an unrelated file
change) must not silently drop "we're waiting on a confirmation reply,"
or the conversation log that led up to it.
"""
import datetime
import os
import sqlite3
import threading
from dataclasses import dataclass

_DB_PATH = "data/sessions.sqlite"
_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is not None:
        return _conn
    os.makedirs(os.path.dirname(_DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    # Without this, SQLite fails a write immediately ("database is locked" /
    # "disk I/O error") the instant another connection briefly holds the
    # write lock, instead of waiting for it to free up — and this file can
    # legitimately have more than one connection: this process's own
    # checkpointer connection is separate (agent/graph.py), plus another
    # server process/reload cycle pointed at the same repo.
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            awaiting_confirmation INTEGER NOT NULL DEFAULT 0,
            awaiting_clarification INTEGER NOT NULL DEFAULT 0,
            pending_transcript TEXT NOT NULL DEFAULT '',
            pending_question TEXT NOT NULL DEFAULT '',
            input_mode TEXT NOT NULL DEFAULT 'text',
            current_task_id TEXT
        );
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            task_id TEXT,
            role TEXT NOT NULL,
            message_type TEXT NOT NULL,
            text TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        """
    )
    conn.commit()
    _conn = conn
    return _conn


@dataclass
class Session:
    session_id: str
    awaiting_confirmation: bool = False
    # A finished task whose only step was "clarify" (e.g. "what filename?")
    # isn't paused/resumable like an ASK_CONFIRM interrupt — the graph run
    # is over, done=True. Without tracking this, the user's next short
    # reply ("rr", "yes") gets planned as a brand-new, context-free
    # transcript and just produces another clarify question, forever.
    # These fields let the next message be stitched onto the conversation
    # so far and replanned as one combined request instead.
    awaiting_clarification: bool = False
    pending_transcript: str = ""
    pending_question: str = ""
    input_mode: str = "text"
    current_task_id: str | None = None


_sessions: dict[str, Session] = {}


def get_or_create(session_id: str) -> Session:
    if session_id in _sessions:
        return _sessions[session_id]

    conn = _get_conn()
    with _lock:
        row = conn.execute(
            "SELECT awaiting_confirmation, awaiting_clarification, pending_transcript, "
            "pending_question, input_mode, current_task_id FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()

    if row is None:
        session = Session(session_id=session_id)
    else:
        session = Session(
            session_id=session_id,
            awaiting_confirmation=bool(row[0]),
            awaiting_clarification=bool(row[1]),
            pending_transcript=row[2],
            pending_question=row[3],
            input_mode=row[4],
            current_task_id=row[5],
        )
    _sessions[session_id] = session
    return session


def save(session_id: str) -> None:
    """Persist the current state of one session (call after any mutation
    to fields that affect message routing — see server/ws.py's uses)."""
    session = _sessions.get(session_id)
    if session is None:
        return
    conn = _get_conn()
    with _lock:
        conn.execute(
            """
            INSERT INTO sessions (session_id, awaiting_confirmation, awaiting_clarification,
                pending_transcript, pending_question, input_mode, current_task_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                awaiting_confirmation = excluded.awaiting_confirmation,
                awaiting_clarification = excluded.awaiting_clarification,
                pending_transcript = excluded.pending_transcript,
                pending_question = excluded.pending_question,
                input_mode = excluded.input_mode,
                current_task_id = excluded.current_task_id
            """,
            (
                session.session_id,
                int(session.awaiting_confirmation),
                int(session.awaiting_clarification),
                session.pending_transcript,
                session.pending_question,
                session.input_mode,
                session.current_task_id,
            ),
        )
        conn.commit()



def record_message(session_id: str, task_id: str | None, role: str, message_type: str, text: str | None) -> None:
    """Append one turn to conversation_history, linked to `session_id` via
    a foreign key. Distinct from agent/graph.py's per-task checkpoint
    state (that's resumable graph state, not a chat log) and
    components/c12_audit_logger's per-step, PII-masked audit trail (that's
    a compliance record of actions taken, not of what was said).

    Row is written even if `session_id` has no matching sessions row yet
    (get_or_create() always creates one first in practice, but this isn't
    relied on as an enforced constraint — see the module docstring on why
    FK enforcement is left off).
    """
    conn = _get_conn()
    with _lock:
        conn.execute(
            "INSERT INTO conversation_history (session_id, task_id, role, message_type, text, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, task_id, role, message_type, text, datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )
        conn.commit()


def get_history(session_id: str) -> list[dict]:
    """Full conversation_history for one session, oldest first."""
    conn = _get_conn()
    with _lock:
        rows = conn.execute(
            "SELECT task_id, role, message_type, text, created_at FROM conversation_history "
            "WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    return [{"task_id": r[0], "role": r[1], "message_type": r[2], "text": r[3], "created_at": r[4]} for r in rows]


def _reset_all_for_tests() -> None:
    """Test-only: wipe both tables and the in-memory cache so a fixed
    session_id (e.g. "session-1") reused across separate pytest
    invocations doesn't load a stale row left over from a previous run —
    see server/tests/test_ws.py's setup_function()."""
    _sessions.clear()
    conn = _get_conn()
    with _lock:
        conn.execute("DELETE FROM conversation_history")
        conn.execute("DELETE FROM sessions")
        conn.commit()


def drop(session_id: str) -> None:
    """Evicts the in-memory Session on disconnect so the next connection
    for this session_id reloads its row fresh from disk instead of
    reusing a stale cached object.

    Deliberately does NOT delete the sqlite row. A disconnect here is
    indistinguishable from the process itself being torn down mid-task
    (see module docstring's `uvicorn --reload` scenario) — deleting on
    every disconnect would erase the very "awaiting confirmation" state
    persistence exists to survive, right as it happens, defeating the
    whole point. Reconnecting with the same session_id (the documented
    reuse pattern — see README.md) picks the routing state back up via
    get_or_create(); server/ws.py's _confirmation_actually_pending()
    cross-checks it against the graph's own checkpoint before ever
    trusting it, so a stale row can't wedge a session that has nothing
    left to resume."""
    _sessions.pop(session_id, None)
