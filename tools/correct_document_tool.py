"""Tool wrapper around docuHandlers/handlers/document_corrector.py
(self-contained — no sys.path shim needed, unlike the comparison/pdf_to_docx
handlers)."""
from typing import Any

from docuHandlers.handlers.document_corrector import correct_document


class CorrectDocumentTool:
    app_name = "correct_document"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]
        result = correct_document(target["file"], target.get("replacements"), target.get("output_path"))
        return {"success": True, **result}
