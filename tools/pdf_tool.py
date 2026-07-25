"""Tool wrapper around components/c06_pdf_adapter. Read-only, per the
component's own contract."""
from typing import Any

from components.c06_pdf_adapter.src.pdf_adapter import extract


class PDFTool:
    app_name = "pdf"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        if step.get("type") == "write":
            raise ValueError("the pdf tool is read-only; write steps must target a different app")
        target = step["target"]
        result = extract({"file": target["file"], "query": target.get("query")})
        return {"success": True, **result}
