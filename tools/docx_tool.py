"""Tool wrapper around components/c18_docx_adapter.

Adds a `create` path — unlike pptx/xlsx, no LLM call is needed to
structure a document's content: paragraphs are just paragraphs, so raw
source material is split on blank lines directly. An explicit "paragraphs"
list in the step still takes priority when the planner supplied one.
"""
from typing import Any

from components.c18_docx_adapter.src.docx_adapter import read_or_write
from tools import workspace


class DocxTool:
    app_name = "docx"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]

        if step.get("type") == "create":
            return self._create(step, target)

        operation = "write" if step.get("type") == "write" else "read"
        request: dict[str, Any] = {"file": target["file"], "operation": operation}
        for key in ("paragraph_index", "table_index", "row", "col"):
            if key in target:
                request[key] = target[key]
        if operation == "write":
            request["value"] = step.get("value")
        return read_or_write(request)

    def _create(self, step: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
        file_path = workspace.resolve(target["file"])
        title = target.get("title")
        paragraphs = target.get("paragraphs")

        if not paragraphs:
            source = step.get("value")
            if not source:
                raise ValueError('docx create step needs "paragraphs", or a "value"/value_ref with source material')
            paragraphs = [p.strip() for p in source.split("\n") if p.strip()]

        return read_or_write({"file": file_path, "operation": "create", "title": title, "paragraphs": paragraphs})
