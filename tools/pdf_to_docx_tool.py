"""Tool wrapper around docuHandlers/handlers/document_handler.py.

Same sys.path note as tools/compare_summarize_tool.py — this handler's
own bare `from extractors...` imports need docuHandlers/ on sys.path.
"""
import os
import sys
from typing import Any

_DOCUHANDLERS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docuHandlers"))
if _DOCUHANDLERS_DIR not in sys.path:
    sys.path.insert(0, _DOCUHANDLERS_DIR)

from handlers.document_handler import transfer_pdf_to_docx  # noqa: E402


class PdfToDocxTool:
    app_name = "pdf_to_docx"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]
        result = transfer_pdf_to_docx(target["source_pdf"], target["target_document"], target.get("output_path"))
        return {"success": True, **result}
