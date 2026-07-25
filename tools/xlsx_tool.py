"""Tool wrapper around components/c07_xlsx_adapter.

Adds a `create` path — same pattern as tools/pptx_tool.py: if the step
didn't supply explicit "rows", ask Groq to turn whatever source material
it has into a simple table before handing off to the component's
mechanical create().
"""
from typing import Any

from components.c07_xlsx_adapter.src.xlsx_adapter import read_or_write
from tools import workspace
from tools.groq_client import structured_completion

_ROWS_SYSTEM_PROMPT = """Turn the given source material into simple \
tabular data. Output strictly this JSON shape, nothing else:
{"sheet_name": "<short sheet name>", "rows": [["<col>", "<col>", ...]]}
The first row should be column headers. Use only facts present in the \
source material below — never invent data."""


def _extract_field_value(raw_text: Any, sheet_name: str | None, cell_ref: str) -> Any:
    if not isinstance(raw_text, str) or "\n" not in raw_text:
        return raw_text

    col_char = "".join(c for c in cell_ref if c.isalpha()).upper()
    col_map = {"A": "buyer", "B": "payer", "C": "bill details"}
    target_field = col_map.get(col_char)
    if not target_field:
        return raw_text

    lines = raw_text.splitlines()
    if sheet_name:
        clean_sheet = sheet_name.replace("&", "").replace(";", "").strip().lower()
        section_lines = []
        in_section = False
        for line in lines:
            clean_line = line.replace("&", "").replace(";", "").strip().lower()
            if clean_line == clean_sheet or (clean_line.startswith(clean_sheet) and len(clean_line) <= len(clean_sheet) + 2):
                in_section = True
                continue
            if in_section:
                if any(clean_line == hdr or (clean_line.startswith(hdr) and len(clean_line) <= len(hdr) + 2) for hdr in ["dtdl", "att", "vodafone"]):
                    break
                section_lines.append(line)
        if section_lines:
            lines = section_lines

    for line in lines:
        line_clean = line.strip()
        if line_clean.lower().startswith(target_field):
            return line_clean[len(target_field):].strip()

    return raw_text


class XLSXTool:
    app_name = "xlsx"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]

        if step.get("type") == "create":
            return self._create(step, target)

        operation = "write" if step.get("type") == "write" else "read"
        request = {"file": target["file"], "cell": target["cell"], "sheet": target.get("sheet"), "operation": operation}
        if operation == "write":
            raw_val = step.get("value") if step.get("value") is not None else target.get("value")
            request["value"] = _extract_field_value(raw_val, target.get("sheet"), target["cell"])
        return read_or_write(request)

    def _create(self, step: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
        file_path = workspace.resolve(target["file"])
        sheet_name = target.get("sheet_name")
        rows = target.get("rows")

        if not rows:
            source = step.get("value") or target.get("topic")
            if not source:
                raise ValueError('xlsx create step needs "rows", or a "value"/value_ref with source material')
            outline = structured_completion(
                _ROWS_SYSTEM_PROMPT,
                f"Topic: {target.get('topic', '')}\n\nSource material:\n{source}",
            )
            sheet_name = sheet_name or outline.get("sheet_name")
            rows = outline.get("rows", [])

        return read_or_write({"file": file_path, "operation": "create", "sheet_name": sheet_name, "rows": rows})
