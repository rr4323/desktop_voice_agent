"""Tool wrapper around docuHandlers/handlers/presentation_handler.py.

Same sys.path note as tools/compare_summarize_tool.py — that handler's own
bare `from extractors...` and (inside process_presentation_with_llm) `from
orchestrator.llm_client...` imports only resolve once docuHandlers/ itself
is on sys.path.

Registered under a distinct app name ("presentation_llm") rather than
"pptx" — tools/pptx_tool.py already owns that name for
components/c08_pptx_adapter's structured single-placeholder writes; this
tool is the free-form, LLM-planned multi-slide alternative (insert/
delete/replace/update slides in one prompt-driven call).
"""
import os
import sys
from typing import Any

_DOCUHANDLERS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docuHandlers"))
if _DOCUHANDLERS_DIR not in sys.path:
    sys.path.insert(0, _DOCUHANDLERS_DIR)

from handlers.presentation_handler import process_presentation_with_llm  # noqa: E402


class PresentationLLMTool:
    app_name = "presentation_llm"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]

        if step.get("type") == "read":
            # agent/nodes/_helpers.py's peek_current_value() probes a
            # write/create step's current target state by calling this
            # same tool with type="read" before policy_check ever confirms
            # anything. There's no cheap single "current value" for a
            # whole presentation the way there is for one cell/placeholder
            # (same "nothing to read yet" situation _create steps document
            # in that helper) — importantly, must NOT fall through to
            # process_presentation_with_llm below, which calls an LLM and
            # writes an output file as a side effect.
            return {"value": None}

        result = process_presentation_with_llm(
            target["file"],
            target["prompt"],
            target.get("source_files"),
            target.get("output_path"),
        )
        return {"success": True, **result}
