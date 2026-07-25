# Voice-Controlled Desktop Agent & docuHandlers

**DTDL HackFest — Problem Statement 2**

A voice and text-driven AI agent that operates local desktop document workflows spanning **PDF, Excel (XLSX/CSV), PowerPoint (PPTX), Word (DOCX)** files, and browser automation.

See [`docs/TDD.md`](docs/TDD.md) for the full technical design document and [`docs/Component_IO_Spec.md`](docs/Component_IO_Spec.md) for exact component contracts.

---

## 🎯 System Purpose & Core Goals

### Primary Objective
Telecom back-office document workflows require extracting data from network reports/invoices (PDF), updating operational spreadsheets (XLSX/CSV), and refreshing executive slide decks (PPTX) or reports (DOCX). This project provides an autonomous, hands-free agent that accepts **spoken voice or written text instructions** to execute multi-step document operations locally.

### Key Security & Design Principles
1. **Deterministic Safety Boundary:** The LLM *proposes* actions; a separate, non-LLM Python rule engine (*Policy Engine*) decides whether any action is allowed to run.
2. **Prompt-Injection Resistance:** Content read from PDFs, spreadsheets, or webpages is treated strictly as **untrusted data**, never as executable instructions.
3. **Data Sovereignty & GDPR Compliance:** All processing runs 100% locally or on controlled endpoints. PII (phone numbers, subscriber IDs) is automatically masked in audit logs.
4. **Empirical Verification:** The agent never assumes a write succeeded—it re-reads the target file/cell after execution to confirm the postcondition was met.

---

## 🔄 End-to-End Process Flow

The processing pipeline is driven by a stateful **LangGraph `StateGraph`** (`agent/graph.py`) that manages task execution across 8 distinct stages:

```
[ User Input (Text / Audio WAV) ]
              │
              ▼
   [ Stage 1: ASR (Whisper) ] ── (Low confidence) ──► [ Clarification Prompt ]
              │
              ▼
   [ Stage 2: Task Planner (LLM) ] ── (Ambiguous / Clarify) ──► [ Stage 8: Respond / TTS ]
              │                                                        ▲
              ▼                                                        │
   [ Stage 3: Policy Engine ] ── DENY ──► [ Deny Node ] ──► [ Audit ]  │
       │            │                                         │        │
     ALLOW     ASK_CONFIRM                                    │        │
       │            │                                         │        │
       │            ▼                                         │        │
       │    [ Stage 4: Confirm Loop ] (Pauses via interrupt())│        │
       │        │         │                                   │        │
       │      Approved  Declined                              │        │
       │        │         │                                   │        │
       ▼        ▼         ▼                                   ▼        │
    [ Stage 5: Execute Adapter ] [ Cancel Node ] ─────────► [ Audit ]  │
       │                            │                         │        │
       ▼                            └─────────────────────► [ Audit ]  │
    [ Stage 6: Verification ] ────────────────────────────► [ Audit ]  │
       │                                                               │
       └── (All steps complete) ───────────────────────────────────────┘
```

### Stage-by-Stage Breakdown

1. **Stage 1: Speech Recognition (ASR - `c01`)**
   - Microphones capture spoken audio or receive base64 WAV payload over WebSocket.
   - **Faster-Whisper** transcribes speech to text with confidence scoring. Low-confidence speech triggers a clarification prompt instead of guessing.

2. **Stage 2: Task Planning (LLM - `c04`)**
   - Receives transcript and workspace context (`open_files`, `working_memory`).
   - Converts natural language into a schema-validated `TaskPlan` containing structured `ActionRequest` steps (`read`, `write`, `create`, `clarify`). Never executes actions directly.

3. **Stage 3: Policy Engine Authorization (`c05`)**
   - Pure Python rule engine evaluates each `ActionRequest`:
     - **`ALLOW`**: Safe read-only actions or writing to empty cells.
     - **`ASK_CONFIRM`**: Overwriting non-empty data, destructive operations, or accessing sensitive fields.
     - **`DENY`**: Injection attempts or forbidden operations.

4. **Stage 4: Confirmation Interruption Loop (`c02` & LangGraph Interrupt)**
   - When `ASK_CONFIRM` is triggered, LangGraph executes an `interrupt()`, pausing graph state via SQLite checkpointer (`data/agent_checkpoints.sqlite`).
   - Sends a `confirm_request` to the client. When the user responds (*"Yes, proceed"* or *"Cancel"*), the response is deterministically parsed and graph execution resumes.

5. **Stage 5: Execution Adapters & `docuHandlers` (`c06`–`c18` & `tools/`)**
   - Approved actions are dispatched via `tools/registry.py` to target adapters:
     - 📄 **PDF (`c06`)**: Text/table extraction with page & element provenance.
     - 📊 **XLSX / CSV (`c07`)**: Cell, formula, and sheet read-write.
     - 📽️ **PPTX (`c08`)**: Slide text, tables, and shape placeholders.
     - 📝 **DOCX (`c18`)**: Paragraph and table cell read-write.
     - 🌐 **Browser (`c15`/`c17`)**: Playwright automation & autonomous web sub-agent.
     - ⚙️ **`docuHandlers/`**: High-level modules for PDF conversion, document correction, spreadsheet merging, presentation updates, and file organization.
   - Values are stored in **Working Memory (`c09`)** to avoid numeric LLM hallucinations.

6. **Stage 6: Postcondition Verification (`c10`)**
   - After a write, the target file/cell is re-read on disk to confirm that the value actually landed.

7. **Stage 7: Audit Logging (`c12`)**
   - One structured, PII-masked compliance log line is written per step (`data/audit.jsonl`).

8. **Stage 8: Output & Text-to-Speech (TTS - `c03`)**
   - Summarizes verified results. If input mode was audio, **Piper TTS** synthesizes speech and streams audio back over WebSocket.

---

## 📦 Data Version Control (DVC)

Sample datasets, document templates, and workspace files are tracked using **DVC (Data Version Control)** to decouple large binaries from Git while keeping versions reproducible:

- **DVC Tracking Files:**
  - `docuHandlers/samples.dvc`
  - `workspace_files.dvc`

### DVC Usage Commands

```bash
# Initialize DVC repository
dvc init

# Add data directories to DVC tracking
dvc add docuHandlers/samples workspace_files

# Check DVC status
dvc status

# Push / Pull tracked data snapshots (when remote is configured)
dvc push
dvc pull
```

---

## 📜 `docuHandlers` Per-Run Execution Logging

Every handler inside **`docuHandlers/`** automatically logs detailed execution metadata per run into [`docuHandlers/logs/`](docuHandlers/logs/):

1. **Consolidated Log (`docuHandlers/logs/docuhandlers.log`):** Cumulative timestamped history of all handler invocations.
2. **Individual Run Log (`docuHandlers/logs/run_<timestamp>_<handler>.log`):** Dedicated per-run execution file recording:
   - **Timestamp (ISO8601 UTC)**
   - **Handler Name** (e.g. `spreadsheet_handler`, `document_handler`, `document_corrector`, `comparison_handler`, `file_organizer`)
   - **Execution Status** (`SUCCESS` / `FAILED`)
   - **Execution Duration** (in seconds)
   - **Input Arguments & Output Result Payloads**
   - **Error Stack Trace** (if an error occurs)

---

## 📂 Project Organization & Components

Every component gets its own folder under [`components/`](components/):

| # | Component | Responsibility |
|---|---|---|
| **01** | [`c01_asr`](components/c01_asr/) | Converts audio input into text transcript with confidence scoring (Faster-Whisper). |
| **02** | [`c02_confirmation_parser`](components/c02_confirmation_parser/) | Deterministically parses spoken/written responses to confirmation prompts. |
| **03** | [`c03_tts`](components/c03_tts/) | Synthesizes response text into spoken audio output with barge-in interruption support (Piper TTS). |
| **04** | [`c04_planner`](components/c04_planner/) | Converts transcript + task context into a structured JSON `TaskPlan`. Never executes actions directly. |
| **05** | [`c05_policy_engine`](components/c05_policy_engine/) | Sole authority that decides whether an action executes (`ALLOW`, `ASK_CONFIRM`, `DENY`). Pure rule-engine. |
| **06** | [`c06_pdf_adapter`](components/c06_pdf_adapter/) | Extracts text/table data from PDF files with page & element provenance. |
| **07** | [`c07_xlsx_adapter`](components/c07_xlsx_adapter/) | Reads/writes Excel (`.xlsx`) and CSV (`.csv`) spreadsheet cells, formulas, and sheets. |
| **08** | [`c08_pptx_adapter`](components/c08_pptx_adapter/) | Reads/writes PowerPoint slide text, tables, and placeholders. |
| **09** | [`c09_working_memory`](components/c09_working_memory/) | Holds extracted values with provenance for the duration of a task to prevent numeric hallucination. |
| **10** | [`c10_verification`](components/c10_verification/) | Re-reads target file postconditions after writes to empirically verify success. |
| **11** | [`c11_state_manager`](components/c11_state_manager/) | Tracks step status across a task; supports pause, resume, correction, and cancellation. |
| **12** | [`c12_audit_logger`](components/c12_audit_logger/) | Writes structured, PII-masked compliance audit logs per step. |
| **13** | [`c13_orchestrator`](components/c13_orchestrator/) | Wires all components together for end-to-end task execution. |
| **14** | [`c14_accessibility_adapter`](components/c14_accessibility_adapter/) | AT-SPI desktop accessibility tree fallback adapter for GUI elements. |
| **15** | [`c15_browser_adapter`](components/c15_browser_adapter/) | Reads/writes values on web pages via Playwright selectors. |
| **16** | [`c16_libreoffice_adapter`](components/c16_libreoffice_adapter/) | Headless document format conversion (`soffice --headless`). |
| **17** | [`c17_browser_agent`](components/c17_browser_agent/) | Autonomous LangGraph ReAct agent driving browser tasks. |
| **18** | [`c18_docx_adapter`](components/c18_docx_adapter/) | Reads/writes Word (`.docx`) document paragraphs and table cells. |

### 🛠️ Sub-System Architecture
- **`docuHandlers/`**: High-level modules for PDF extraction, document correction (`document_corrector.py`), comparison (`comparison_handler.py`), presentation updating (`presentation_handler.py`), spreadsheet merging (`spreadsheet_handler.py`), and file organization (`file_organizer.py`).
- **`agent/`**: LangGraph StateGraph orchestration (`graph.py`, `state.py`, `nodes/`).
- **`tools/`**: Execution adapters registry (`tools/registry.py`).
- **`server/`**: FastAPI app and WebSocket handler (`app.py`, `ws.py`).

---

## ⚡ Setup & Quick Start

### 1. Environment Setup

```bash
# Clone and enter directory
cd desktop_voice_agent

# Create python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (includes DVC, LangGraph, FastAPI, PyMuPDF, etc.)
pip install -r requirements.txt

# Install Playwright browser binaries
python -m playwright install chromium
```

### 2. Environment Variables Configuration

Create a `.env` file in the root directory:
```env
MISTRAL_API_KEY="your_mistral_api_key"
GROQ_API_KEY="your_groq_api_key"
GEMINI_API_KEY="your_gemini_api_key"

# Optional Langfuse Tracing
LANGFUSE_SECRET_KEY=""
LANGFUSE_PUBLIC_KEY=""
LANGFUSE_BASE_URL="https://us.cloud.langfuse.com"
```

---

## 🚀 How to Run

### Option A: Running via CLI (`main.py`)

Run tasks directly from the command line against target files:

```bash
# Execute Invoice Extraction & Filling
python main.py --prompt "Read the invoice information from the PDF and fill the Buyer, Payer, and Bill Details columns only in the AT&T and Vodafone worksheets of the Excel file. Do not modify the DTDL sheet." --files Invoice_Insights_Filled.pdf Invoice_Insights_Template.xlsx

# Modify a CSV / Spreadsheet file
python main.py --prompt "Write 'FY 2023-2024' to cell D1 in workspace_files/Class_Student_Counts.csv." --files workspace_files/Class_Student_Counts.csv
```

---

### Option B: Running via FastAPI / WebSocket Server

Start the application server:

```bash
uvicorn server.app:app --port 8000 --reload
```

Connect to `ws://localhost:8000/ws/agent/<session_id>`:

#### Client $\rightarrow$ Server Payloads:
- **Text Turn:**
  ```json
  {
    "type": "text", 
    "text": "Extract Revenue from docuHandlers/samples/q3_earnings.pdf",
    "context": {
      "open_files": ["docuHandlers/samples/q3_earnings.pdf"],
      "working_memory": {}
    }
  }
  ```
- **Audio Turn:**
  ```json
  {
    "type": "audio",
    "audio_b64": "<base64_encoded_wav_bytes>",
    "mime": "audio/wav"
  }
  ```

#### Server $\rightarrow$ Client Responses:
- **Status Event:** `{"type": "status", "stage": "planning"}`
- **Confirmation Interruption Request:** `{"type": "confirm_request", "prompt": "...", "step_id": N}`
- **Final Result:** `{"type": "final", "text": "...", "results": [...]}`

---

## 🛡️ Backup & Reversibility (`.bak` files)

Before performing any write or overwrite action, the adapter creates a temporary backup snapshot (`file.ext.bak`). This ensures:
1. **Reversibility:** Safe rollback if an operation fails or is cancelled by the user.
2. **Preservation:** The original file remains safe while outputs can be stored as updated files (`*_updated.ext`).

---

## 🧪 Testing & Verification

Run the full unit test suite across all 18 components, adapters, tools, state graph, and WebSocket endpoints:

```bash
pytest
```
