# Part 4 — Execution & Audit Module

This package contains the Part 4 implementation: execution adapters (PDF/XLSX/PPTX/DOCX), working memory, verification, state manager, and audit logger.

Features:
- Adapters: `PDFAdapter`, `XLSXAdapter`, `PPTXAdapter`, `DocxAdapter` (read/write for paragraphs and table cells).
- Working memory: short-lived task-scoped key-value store (`part4/memory.py`).
- Verification: re-reads targets and reports `postcondition_met` and `anomaly_flag` (`part4/verification.py`).
- State manager: simple task graph with rollback support (`part4/state_manager.py`).
- Audit logger: JSON-lines audit with PII masking (`part4/audit_logger.py`).

Demos and tests:
- Run the demo: `python demo/run_demo.py` (creates temp files   and audit logs).
- Run tests: `python -m pytest tests` (requires dependencies from `requirements.txt`).

