# Voice-Controlled Desktop Agent (PDF / XLSX / PPTX)

DTDL HackFest — Problem Statement 2. See [`docs/TDD.md`](docs/TDD.md) for the
full architecture and [`docs/Component_IO_Spec.md`](docs/Component_IO_Spec.md)
for the exact input/output contract of every component.

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

Components 14-16 aren't in the original `Component_IO_Spec.md` — they were
added afterward: 14 and 15 to explicitly demonstrate the "operate the
desktop using appropriate GUI, accessibility, browser, or automation
interfaces" capability beyond the document-format adapters, and 16 to
cover legacy-format conversion (`.doc`/`.xls`/`.ppt`) that the native
libraries can't read or write at all. See the "Extensions beyond the
original spec" section at the bottom of
[`docs/Component_IO_Spec.md`](docs/Component_IO_Spec.md) for their contracts.

**The hard rule that makes parallel work possible:** components never import
or call each other directly. They only exchange the JSON-shaped data
structures defined in [`schemas/`](schemas/) (mirrors TDD §5.2 and the
Component I/O Spec). If you're building component 6 and need component 5's
output, don't wait for someone to finish it — write a fixture in
`schemas/examples/` that matches the documented shape and build against that.
The orchestrator (component 13) is the only place these get wired together
for real, and it's built last.

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
