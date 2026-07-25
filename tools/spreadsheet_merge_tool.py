"""Tool wrapper around docuHandlers/handlers/spreadsheet_handler.py
(self-contained — no sys.path shim needed, unlike the comparison/
presentation_llm/pdf_to_docx handlers).

Registered as "spreadsheet_merge" rather than "xlsx" — tools/xlsx_tool.py
already owns that name for components/c07_xlsx_adapter's single-cell
reads/writes; this tool is the bulk alternative that appends a whole new
column of metrics, matched by row label rather than a cell reference.
"""
from typing import Any

from docuHandlers.handlers.spreadsheet_handler import merge_into_spreadsheet


class SpreadsheetMergeTool:
    app_name = "spreadsheet_merge"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]

        if step.get("type") == "read":
            # See tools/presentation_llm_tool.py's identical guard: this is
            # peek_current_value()'s pre-confirmation probe, not a real
            # request to merge — a bulk multi-cell merge has no single
            # "current value" to report, and must not run for real here.
            return {"value": None}

        result = merge_into_spreadsheet(
            target["file"],
            target["metrics"],
            target["period"],
            target.get("sheet_name"),
        )
        return {"success": True, **result}
