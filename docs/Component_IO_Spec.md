# Component Interface Specification
## Voice-Controlled Desktop Agent (PDF / XLSX / PPTX) — DTDL HackFest

Each component below is designed to be built, run, and tested in isolation — no component calls another directly; they only pass data structures back and forth. This means you can stub every dependency with a JSON fixture and verify a module's behavior without the rest of the pipeline running.

---

## 1. ASR Module (speech → text)

**Responsibility:** Convert microphone audio into a transcript with a confidence signal.

**Input**
- Audio stream/buffer (WAV/PCM) from microphone, or a `.wav` file for testing.

**Output**
```json
{
  "transcript": "update the kpi tracker with the q3 revenue total",
  "confidence": 0.94,
  "low_confidence_spans": []
}
```

**Standalone test**
- Feed pre-recorded `.wav` samples (clean speech, noisy speech, accented speech) directly into the Whisper wrapper.
- Assert: transcript text, confidence score, and that spans below a confidence threshold are flagged in `low_confidence_spans`.
- No other module needs to be running — this is a pure audio-in, JSON-out function.

**Dependencies to mock:** none (this is a leaf module).

---

## 2. Confirmation/Intent Parser (deterministic yes/no)

**Responsibility:** Parse a spoken response to a confirmation prompt into a strict decision — deliberately *not* an LLM call, so behavior is deterministic and auditable.

**Input**
```json
{ "transcript": "yes go ahead" }
```

**Output**
```json
{ "confirmed": true, "match_rule": "affirmative_phrase" }
```
or
```json
{ "confirmed": false, "match_rule": "no_match", "needs_reprompt": true }
```

**Standalone test**
- Feed a list of transcript strings (`"yes"`, `"go ahead"`, `"no don't"`, `"cancel that"`, `"umm not sure"`) and assert the correct `confirmed`/`needs_reprompt` output for each — this is a pure string-matching module, testable with a simple table-driven unit test, no audio or LLM required.

**Dependencies to mock:** none.

---

## 3. TTS Module (text → speech)

**Responsibility:** Convert a response string into spoken audio output, with support for interruption (barge-in).

**Input**
```json
{ "text": "Cell B7 currently contains a value — should I overwrite it with 2.4 million from page 3?" }
```

**Output:** audio stream/buffer played to speaker; returns a handle that can be cancelled mid-playback.

**Standalone test**
- Call the module directly with sample strings and confirm audio is produced.
- Test barge-in by triggering a cancel signal mid-playback and asserting audio stops within a bounded latency.

**Dependencies to mock:** none.

---

## 4. Task Planner (LLM)

**Responsibility:** Convert a transcript (+ current task/working-memory context) into a structured, schema-valid task plan. Never executes anything itself.

**Input**
```json
{
  "transcript": "pull the q3 revenue total from the network report and put it into the kpi tracker",
  "context": { "open_files": ["network_report.pdf", "kpi_tracker.xlsx"], "working_memory": {} }
}
```

**Output**
```json
{
  "goal": "Copy Q3 revenue total from network_report.pdf into kpi_tracker.xlsx",
  "steps": [
    { "step_id": 1, "type": "read", "target": { "app": "pdf", "file": "network_report.pdf", "query": "Q3 revenue total" } },
    { "step_id": 2, "type": "write", "target": { "app": "xlsx", "file": "kpi_tracker.xlsx", "cell": "B7" }, "value_ref": "step_1.value", "depends_on": [1] }
  ]
}
```

**Standalone test**
- Run the planner against a bank of sample transcripts (clear requests, ambiguous requests, requests referencing files not currently open) and validate the output against the JSON schema.
- For ambiguous input, assert the planner emits a `clarify` step instead of guessing.
- No file I/O or policy engine needed — this module only produces a plan; it never touches real files.

**Dependencies to mock:** none required, but tests should include adversarial transcripts (injected-looking phrasing) to confirm the planner doesn't emit raw shell/file-delete actions from user speech alone — that's a planner-quality test, separate from the policy engine's hard enforcement.

---

## 5. Policy Engine (deterministic authorization)

**Responsibility:** The sole authority that decides whether a proposed action executes. Pure function — no model call.

**Input**
```json
{
  "step_id": 2,
  "type": "write",
  "target": { "app": "xlsx", "file": "kpi_tracker.xlsx", "cell": "B7" },
  "current_cell_value": "1.8M"
}
```

**Output**
```json
{
  "step_id": 2,
  "decision": "ASK_CONFIRM",
  "tier": "reversible-write-overwrite",
  "reason": "Target cell B7 already contains a non-empty value"
}
```

**Standalone test**
- This is the easiest module to test exhaustively: build a table of `(action_type, target_state, tier) — expected_decision` cases and assert every row.
- Include the telecom-specific tiers explicitly: PII field write — `ASK_CONFIRM` + mask flag; destructive delete — `ASK_CONFIRM`; action sourced from untrusted document content — `DENY`.
- Because it's deterministic, this module needs no mocks at all — just call the function with fixture inputs and assert exact output equality. This is your highest-confidence, fastest-to-test component; treat it as the foundation of your eval suite.

**Dependencies to mock:** none.

---

## 6. PDF Adapter

**Responsibility:** Extract text/table data from a PDF with page/element provenance. Read-only.

**Input**
```json
{ "file": "network_report.pdf", "query": "Q3 revenue total" }
```

**Output**
```json
{
  "value": "2.4M",
  "provenance": { "file": "network_report.pdf", "page": 3, "element": "table_2/row_4/col_3" },
  "extraction_method": "text_layer"
}
```

**Standalone test**
- Run directly against a folder of sample PDFs (clean text-layer PDF, scanned/image-only PDF, PDF with tables) and assert correct value + provenance extraction.
- Test the OCR fallback path by feeding a scanned PDF and confirming `extraction_method: "ocr"` with a lower confidence score.
- No planner, policy engine, or voice pipeline needed — this is a file-in, JSON-out function you can run from the command line against a test PDF.

**Dependencies to mock:** none (operates directly on files on disk).

---

## 7. XLSX Adapter

**Responsibility:** Read/write spreadsheet cells, formulas, and sheets.

**Input (write)**
```json
{ "file": "kpi_tracker.xlsx", "cell": "B7", "value": "2.4M", "operation": "write" }
```

**Output**
```json
{ "success": true, "cell": "B7", "previous_value": "1.8M", "new_value": "2.4M" }
```

**Input (read)**
```json
{ "file": "kpi_tracker.xlsx", "cell": "B7", "operation": "read" }
```

**Output**
```json
{ "value": "2.4M" }
```

**Standalone test**
- Run against a sample `.xlsx` file copy (never the original — use a throwaway copy per test run).
- Test write-then-read round trip, write to an out-of-range cell (should error cleanly), and formula-preserving writes.
- Fully testable in isolation with `openpyxl` and a local file — no other component required.

**Dependencies to mock:** none.

---

## 8. PPTX Adapter

**Responsibility:** Read/write slide text, tables, and placeholders.

**Input (write)**
```json
{ "file": "exec_briefing.pptx", "slide": 4, "placeholder": "churn_value", "value": "3.1%", "operation": "write" }
```

**Output**
```json
{ "success": true, "slide": 4, "placeholder": "churn_value", "previous_value": "2.9%", "new_value": "3.1%" }
```

**Standalone test**
- Run against a sample `.pptx` copy; verify text substitution lands in the correct placeholder without breaking slide formatting (assert formatting/theme attributes unchanged before/after).
- Test the "unsupported" path explicitly: request an edit to a chart embedded as an image, and assert the adapter returns a clean `unsupported_operation` error rather than silently failing.

**Dependencies to mock:** none.

---

## 9. Working Memory Store

**Responsibility:** Hold extracted values with provenance for the duration of a task, keyed by step ID, so later steps reference data rather than having it re-generated by the LLM.

**Input**
```json
{ "operation": "set", "key": "step_1.value", "value": "2.4M", "provenance": { "file": "network_report.pdf", "page": 3 } }
```
```json
{ "operation": "get", "key": "step_1.value" }
```

**Output**
```json
{ "key": "step_1.value", "value": "2.4M", "provenance": { "file": "network_report.pdf", "page": 3 } }
```

**Standalone test**
- Simple key-value store — test set/get/clear operations and TTL/scope-per-task-cleanup directly with unit tests. No dependencies.

**Dependencies to mock:** none.

---

## 10. Verification Module

**Responsibility:** Re-check that an executed action's postcondition actually holds, and flag implausible values before they're reported as success.

**Input**
```json
{
  "action_result": { "cell": "B7", "expected_value": "2.4M" },
  "current_read": { "cell": "B7", "value": "2.4M" },
  "historical_context": { "previous_quarter_value": "1.8M" }
}
```

**Output**
```json
{ "verified": true, "postcondition_met": true, "anomaly_flag": false }
```

**Standalone test**
- Feed matched and mismatched `(expected, actual)` pairs and confirm `postcondition_met` flips correctly.
- Feed a value with an implausible delta from `historical_context` (e.g., churn rate jumping 40%) and confirm `anomaly_flag: true` is raised even when `postcondition_met` is true — this is what lets you demo the "flags a suspicious value" behavior.
- Mock the adapter's read call with fixture data — no live file needed to unit-test the comparison logic.

**Dependencies to mock:** an adapter's "read" response (use fixtures).

---

## 11. State Manager (task graph)

**Responsibility:** Track step status (`pending / in_progress / done / failed / paused`) across a task; support pause, resume, correction, cancellation.

**Input**
```json
{ "operation": "update_status", "step_id": 2, "status": "done" }
```
```json
{ "operation": "pause", "task_id": "t123" }
```
```json
{ "operation": "correct", "task_id": "t123", "step_id": 2, "new_target": { "cell": "C7" } }
```

**Output**
```json
{ "task_id": "t123", "steps": [{ "step_id": 1, "status": "done" }, { "step_id": 2, "status": "paused" }] }
```

**Standalone test**
- Drive the state machine through a scripted sequence of operations (start — pause — resume — correct — cancel) and assert the graph transitions correctly at each point — this is pure in-memory logic, no I/O required.
- Test the "resume from last completed step" path explicitly: kill the process mid-task, reload from the persisted graph, and confirm it doesn't re-execute completed steps.

**Dependencies to mock:** none (persist to local SQLite/JSON for the reload test).

---

## 12. Audit Logger

**Responsibility:** Write one structured, PII-masked log entry per step.

**Input**
```json
{
  "transcript_snippet": "update the kpi tracker with the q3 revenue total",
  "action": { "type": "write", "target": "kpi_tracker.xlsx!B7" },
  "decision": { "decision": "ASK_CONFIRM", "reason": "overwrite of existing value" },
  "confirmation": "user_approved",
  "result": "success",
  "verification": "pass",
  "raw_fields": { "msisdn": "491701234567" }
}
```

**Output** (written to disk)
```json
{
  "timestamp": "2026-07-24T10:15:03Z",
  "transcript_snippet": "update the kpi tracker with the q3 revenue total",
  "action": { "type": "write", "target": "kpi_tracker.xlsx!B7" },
  "decision": { "decision": "ASK_CONFIRM", "reason": "overwrite of existing value" },
  "confirmation": "user_approved",
  "result": "success",
  "verification": "pass",
  "masked_fields": ["msisdn"]
}
```

**Standalone test**
- Feed entries containing known PII field names (`msisdn`, `cdr_id`, `billing_account`) and assert they are masked in the written output, never appear in plaintext, and that `masked_fields` correctly lists what was redacted.
- Test log-file append behavior and confirm every step of a multi-step task produces exactly one entry.

**Dependencies to mock:** none — this is a pure transform-and-write module.

---

## 13. Orchestrator (integration layer)

**Responsibility:** Wires the above components together in sequence per the data flow in the TDD. This is the only component that isn't independently testable in isolation — it's the integration test.

**Input:** a spoken task request (audio) or, for automated testing, a transcript string bypassing ASR.

**Output:** completed task with full audit trail.

**Standalone test**
- Run end-to-end against the example trace in the TDD (§10) using real sample files, and against each case in the evaluation suite (§11): ambiguous speech, mid-task correction, cancellation, unsafe/injected request, unsupported task.
- Because every component below it has already been unit-tested independently, orchestrator-level tests should focus on sequencing and hand-off correctness (does step 2's `ASK_CONFIRM` correctly pause and wait, does a `DENY` correctly short-circuit the remaining steps) rather than re-testing each component's internal logic.

**Dependencies to mock:** ideally none by the time you reach integration testing — but for early orchestrator development before all adapters are ready, stub any not-yet-built component with a fixture that returns the fixed JSON shape shown above.

---

## Suggested build/test order

1. Policy Engine (§5) — no dependencies, purely deterministic, defines your safety contract early.
2. Confirmation Parser (§2) and Working Memory (§9) — also dependency-free, quick wins.
3. PDF / XLSX / PPTX Adapters (§6–8) — file-in/file-out, testable with sample documents, no voice or LLM needed.
4. Verification (§10), State Manager (§11), Audit Logger (§12) — testable with fixture data from the modules above.
5. ASR / TTS (§1, §3) — hardware-dependent, bring in once the logic layer is solid.
6. Task Planner (§4) — bring in once you have real `ActionRequest` schemas to validate against.
7. Orchestrator (§13) — last, wiring everything together for the end-to-end demo trace.
