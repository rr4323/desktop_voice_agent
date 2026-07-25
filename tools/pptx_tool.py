"""Tool wrapper around components/c08_pptx_adapter.

Adds a `create` path on top of the component's mechanical `create()`: if
the step didn't come with an explicit "slides" outline, this asks Groq to
turn whatever source material it does have (typically a prior step's
`value`, e.g. web search results via the browser_agent sub-agent) into a
deck outline. The component itself stays a pure "given a structure, build
a deck" function — the "turn raw text into a structure" step is agent-
level orchestration, not something a spec component should need an LLM
call for.
"""
from typing import Any

from components.c08_pptx_adapter.src.pptx_adapter import read_or_write
from tools import workspace
from tools.groq_client import structured_completion

_OUTLINE_SYSTEM_PROMPT = """Turn the given source material into a slide \
deck outline. Output strictly this JSON shape, nothing else:
{"title": "<deck title>", "slides": [{"heading": "<slide heading>", "bullets": ["<point>", ...]}]}
Produce 3-6 content slides, each with 2-5 concise bullets drawn only from \
the source material below — never invent facts that aren't in it."""


class PPTXTool:
    app_name = "pptx"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]
        print(target)
        if step.get("type") == "create":
            return self._create(step, target)

        operation = "write" if step.get("type") == "write" else "read"
        request = {
            "file": target["file"],
            "slide": target["slide"],
            "placeholder": target["placeholder"],
            "operation": operation,
        }
        if operation == "write":
            request["value"] = step.get("value")
        return read_or_write(request)

    def _create(self, step: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
        file_path = workspace.resolve(target["file"])
        title = target.get("title")
        slides = target.get("slides")

        if not slides:
            source = step.get("value") or target.get("topic")
            if not source:
                raise ValueError('pptx create step needs "slides", or a "value"/value_ref with source material')
            outline = structured_completion(
                _OUTLINE_SYSTEM_PROMPT,
                f"Topic: {target.get('topic', '')}\n\nSource material:\n{source}",
            )
            title = title or outline.get("title")
            slides = outline.get("slides", [])

        return read_or_write({"file": file_path, "operation": "create", "title": title, "slides": slides})
