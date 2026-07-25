# Voice-Controlled Desktop Agent (PDF / XLSX / PPTX)

DTDL HackFest — Problem Statement 2. See [`docs/TDD.md`](docs/TDD.md) for the
full architecture and [`docs/Component_IO_Spec.md`](docs/Component_IO_Spec.md)
for the exact input/output contract of every component.

## Running the unified agent

Every component below is now wired together into one running agent —
accepts user **text or audio**, drives the TDD §5.1 pipeline (ASR → Plan →
Policy → Confirm → Execute → Verify → Audit → Respond) as a **LangGraph
`StateGraph`** (`agent/graph.py`), and returns **text or audio** — exposed
over **FastAPI + WebSocket**:

```bash
pip install -r requirements.txt
# .env (repo root, gitignored) — server/app.py loads it at startup:
#   GROQ_API_KEY=...           # required — c04_planner and c17_browser_agent's LLM calls
#   LANGFUSE_SECRET_KEY=...    # optional — enables tracing (agent/tracing.py); omit to skip it
#   LANGFUSE_PUBLIC_KEY=...
#   LANGFUSE_BASE_URL=...
uvicorn server.app:app --reload
```

Connect to `ws://localhost:8000/ws/agent/<session_id>` and send one JSON
message per turn — `{"type": "text", "text": "..."}` or
`{"type": "audio", "audio_b64": "...", "mime": "audio/wav"}` — and reply to
any `confirm_request` event the same way. See `server/ws.py`'s module
docstring for the full protocol.

- **`agent/`** — the StateGraph: `state.py` (shared state shape),
  `nodes/` (one module per pipeline stage), `graph.py` (wires them, with a
  LangGraph checkpointer so an `ASK_CONFIRM` genuinely pauses the graph via
  `interrupt()` and resumes exactly where it left off), `tracing.py`
  (optional Langfuse instrumentation — a no-op unless `LANGFUSE_SECRET_KEY`/
  `LANGFUSE_PUBLIC_KEY` are set).
- **`tools/`** — one wrapper per execution adapter, dispatched by
  `target["app"]` (see `tools/registry.py`). Includes `tools/sub_agent/
  browser_agent_tool.py`, which wraps `c17_browser_agent`'s autonomous
  LangGraph browser agent as the `"browser_agent"` tool — since that
  sub-agent doesn't gate its own internal actions, `c05_policy_engine`
  always requires confirmation before this tool runs.
- **`server/`** — the FastAPI app (`app.py`) and WebSocket handler
  (`ws.py`) implementing the protocol above.
- **`components/c13_orchestrator`** still exists as a thin, non-interactive
  synchronous wrapper around `agent/graph.py`, so that component's own
  directory/tests stay meaningful as the "run the whole pipeline
  end-to-end" entry point the spec describes.

## How this repo is organized

Every component from the spec gets its own top-level folder under
[`components/`](components/), numbered to match the spec's section numbers:

| # | Folder | Responsibility |
|---|---|---|
| 01 | [`components/c01_asr/`](components/c01_asr/) | Convert microphone audio into a transcript with a confidence signal. |
| 02 | [`components/c02_confirmation_parser/`](components/c02_confirmation_parser/) | Parse a spoken response to a confirmation prompt into a strict, deterministic decision. |
| 03 | [`components/c03_tts/`](components/c03_tts/) | Convert a response string into spoken audio output, with support for barge-in interruption. |
| 04 | [`components/c04_planner/`](components/c04_planner/) | Convert a transcript + task context into a structured, schema-valid TaskPlan. Never executes anything itself. |
| 05 | [`components/c05_policy_engine/`](components/c05_policy_engine/) | The sole authority that decides whether a proposed action executes. Pure function, no model call. |
| 06 | [`components/c06_pdf_adapter/`](components/c06_pdf_adapter/) | Extract text/table data from a PDF with page/element provenance. Read-only. |
| 07 | [`components/c07_xlsx_adapter/`](components/c07_xlsx_adapter/) | Read/write spreadsheet cells, formulas, and sheets. |
| 08 | [`components/c08_pptx_adapter/`](components/c08_pptx_adapter/) | Read/write slide text, tables, and placeholders. |
| 09 | [`components/c09_working_memory/`](components/c09_working_memory/) | Hold extracted values with provenance for the duration of a task, keyed by step ID. |
| 10 | [`components/c10_verification/`](components/c10_verification/) | Re-check that an executed action's postcondition actually holds, and flag implausible values. |
| 11 | [`components/c11_state_manager/`](components/c11_state_manager/) | Track step status across a task; support pause, resume, correction, cancellation. |
| 12 | [`components/c12_audit_logger/`](components/c12_audit_logger/) | Write one structured, PII-masked log entry per step. |
| 13 | [`components/c13_orchestrator/`](components/c13_orchestrator/) | Wires all other components together per the data flow in the TDD. The only component that is an integration test, not a unit-testable leaf. |
| 14 | [`components/c14_accessibility_adapter/`](components/c14_accessibility_adapter/) | Read/write live desktop UI elements via AT-SPI, for content the format-native adapters can't resolve. Secondary/fallback path. |
| 15 | [`components/c15_browser_adapter/`](components/c15_browser_adapter/) | Read/write a value on a web page (e.g. an internal ops dashboard), same read/write-with-provenance shape as the file adapters. |
| 16 | [`components/c16_libreoffice_adapter/`](components/c16_libreoffice_adapter/) | Headless document conversion (`soffice --headless --convert-to`) for legacy formats or PDF export the native-library adapters don't handle. |
| 17 | [`components/c17_browser_agent/`](components/c17_browser_agent/) | Generic version of `c15`: given a natural-language instruction, autonomously drives a browser via a LangGraph ReAct agent over a local Ollama model. ⚠️ does not route through the Policy Engine — see its README. Wrapped as the `sub_agent` tool, see "Running the unified agent" above. |
| 18 | [`components/c18_docx_adapter/`](components/c18_docx_adapter/) | Read/write Word document paragraphs and table cells — promoted from an earlier prototype, same pattern as 14-17. |

Components 14-18 aren't in the original `Component_IO_Spec.md` — they were
added afterward: 14 and 15 to explicitly demonstrate the "operate the
desktop using appropriate GUI, accessibility, browser, or automation
interfaces" capability beyond the document-format adapters, 16 to cover
legacy-format conversion (`.doc`/`.xls`/`.ppt`) that the native libraries
can't read or write at all, 17 as a generic, LLM-driven version of 15 built
for a specific request to test that capability end-to-end, and 18 to give
`.docx` the same first-class adapter treatment as PDF/XLSX/PPTX already
had. See the "Extensions beyond the original spec" section at the bottom
of [`docs/Component_IO_Spec.md`](docs/Component_IO_Spec.md) for 14-17's
contracts (18 predates that section but follows the same shape).

**The hard rule that makes parallel work possible:** components never import
or call each other directly. They only exchange the JSON-shaped data
structures defined in [`schemas/`](schemas/) (mirrors TDD §5.2 and the
Component I/O Spec). If you're building component 6 and need component 5's
output, don't wait for someone to finish it — write a fixture in
`schemas/examples/` that matches the documented shape and build against that.
`agent/graph.py` and `tools/` are where these get wired together for real
(see "Running the unified agent" above) — every component below is still
independently buildable/testable exactly as described.

## Working on your own component

1. Pick your folder under `components/`.
2. Read its `README.md` — responsibility, exact input/output JSON, and the
   standalone test the spec calls for.
3. Add whatever dependencies you need to that folder's own `requirements.txt`
   (don't touch another component's file).
4. Implement the stub function in `src/`.
5. Write/extend the tests in `tests/`, using fixtures from your component's
   `fixtures/` folder (and/or the shared ones in `schemas/examples/`).
6. Run just your component's tests: `pytest components/<your_folder>`.

Because every component is a pure function over JSON-like data (per the I/O
spec), you should be able to fully build and test yours without any other
component — including the ASR/TTS/LLM ones — being implemented yet.

## Setup

```bash
python3 -m venv --system-site-packages .venv   # --system-site-packages needed for c14 (PyGObject/Atspi)
source .venv/bin/activate
pip install -r requirements.txt   # installs every component's deps, for integration work
# or, to work on just one component:
pip install -r components/c05_policy_engine/requirements.txt
```

`c14_accessibility_adapter` also needs system packages
(`python3-gi gir1.2-atspi-2.0 at-spi2-core xvfb`) and `c15_browser_adapter`
needs its browser binary (`python -m playwright install chromium`) — see
those components' own READMEs.

## Running tests

```bash
pytest                              # everything
pytest components/c05_policy_engine # just one component
```

## Suggested build order (from the spec)

1. Policy Engine (`05`) — no dependencies, defines the safety contract.
2. Confirmation Parser (`02`) and Working Memory (`09`) — dependency-free quick wins.
3. PDF / XLSX / PPTX Adapters (`06`–`08`) — file-in/file-out, no voice or LLM needed.
4. Verification (`10`), State Manager (`11`), Audit Logger (`12`).
5. ASR / TTS (`01`, `03`) — hardware-dependent.
6. Task Planner (`04`) — needs real `ActionRequest` schemas to validate against.
7. Orchestrator (`13`) — last, wires everything together.
8. Accessibility / Browser Adapters (`14`, `15`) — added later to showcase
   the GUI/accessibility/browser capability explicitly; not on the critical
   path for the core PDF→XLSX→PPTX demo trace.

## Git workflow for a two-person team

- One branch per component/task (e.g. `asr-whisper-wrapper`,
  `policy-engine-pii-tier`), opened against `main`.
- Because each person's changes live under their own `components/<n>_<slug>/`
  folder plus maybe a new file in `schemas/examples/`, merge conflicts should
  be rare. If you need to change a shared file in `schemas/`, flag it to the
  other person first — that's the shared contract both of you depend on.
