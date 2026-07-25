"""Tool wrapper around docuHandlers/handlers/comparison_handler.py.

That module (and the extractors it depends on) uses bare `from
extractors...` imports rather than package-qualified ones, which only
resolve when docuHandlers/ itself is on sys.path — the same trick
docuHandlers/main.py already relies on. Applied here rather than editing
docuHandlers' own source.
"""
import os
import sys
from typing import Any

_DOCUHANDLERS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docuHandlers"))
if _DOCUHANDLERS_DIR not in sys.path:
    sys.path.insert(0, _DOCUHANDLERS_DIR)

from handlers.comparison_handler import compare_and_summarize  # noqa: E402


class CompareSummarizeTool:
    app_name = "compare_summarize"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]
        result = compare_and_summarize(target["sources"], target["output_dir"])
        return {"success": True, **result}
