"""PPTX Adapter (component 08): read/write slide text, tables, and
placeholders.

Contract: docs/Component_IO_Spec.md, section 8.

Ported from the working prototype in part4/adapters/pptx_adapter.py (a
`PPTXAdapter` class), reshaped into this component's documented
single-dict-in/single-dict-out `read_or_write` entry point. Writes replace
text inside the existing runs of the first paragraph (rather than
reassigning `.text`, which collapses run-level formatting to a single
default run) so surrounding theme/formatting attributes survive the edit,
and raise a clean, explicit error for a shape that isn't text-editable
(e.g. a chart embedded as an image) instead of failing silently.
"""
import shutil
from typing import Any

from pptx import Presentation


def read_or_write(request: dict[str, Any]) -> dict[str, Any]:
    """request: {"file", "slide", "placeholder", "operation": "read"|"write", "value"? (write only)}

    "operation": "create" is a separate shape — see `create()` below — since
    it builds a brand-new deck rather than addressing an existing slide.
    """
    operation = request["operation"]
    file_path = request["file"]

    if operation == "create":
        return create(request)

    slide_num = request["slide"]
    placeholder_name = request["placeholder"]

    if operation == "read":
        return _read_placeholder(file_path, slide_num, placeholder_name)
    if operation == "write":
        return _write_placeholder(file_path, slide_num, placeholder_name, request["value"])
    raise ValueError(f"unknown operation: {operation!r}")


def create(request: dict[str, Any]) -> dict[str, Any]:
    """Build a brand-new presentation and save it to request["file"].

    request: {"file", "title"?, "slides": [{"heading": str, "bullets": [str, ...]}, ...]}
    A title slide is added first (if "title" is given), followed by one
    "Title and Content" slide per entry in "slides".
    """
    file_path = request["file"]
    title = request.get("title")
    slides_spec = request.get("slides") or []

    prs = Presentation()

    if title:
        title_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_layout)
        slide.shapes.title.text = title

    body_layout = prs.slide_layouts[1]
    for entry in slides_spec:
        slide = prs.slides.add_slide(body_layout)
        slide.shapes.title.text = entry.get("heading", "")

        bullets = entry.get("bullets") or []
        if bullets:
            body_placeholder = slide.placeholders[1]
            text_frame = body_placeholder.text_frame
            text_frame.text = bullets[0]
            for bullet in bullets[1:]:
                paragraph = text_frame.add_paragraph()
                paragraph.text = bullet

    prs.save(file_path)
    return {"success": True, "file": file_path, "slide_count": len(prs.slides)}


def _find_shape(prs: Presentation, slide_num: int, placeholder_name: str):
    try:
        slide = prs.slides[slide_num - 1]
    except IndexError as exc:
        raise LookupError(f"slide {slide_num} does not exist (presentation has {len(prs.slides)} slides)") from exc

    for shape in slide.shapes:
        if shape.name == placeholder_name:
            return slide, shape
    for shape in slide.shapes:
        if placeholder_name.lower() in shape.name.lower():
            return slide, shape
    raise LookupError(f"no shape named {placeholder_name!r} found on slide {slide_num}")


def _require_text_frame(shape, slide_num: int, placeholder_name: str):
    if not shape.has_text_frame:
        raise ValueError(
            f"unsupported_operation: shape {placeholder_name!r} on slide {slide_num} has no editable text "
            "(e.g. a chart embedded as an image) — not something this adapter can read/write"
        )


def _read_placeholder(file_path: str, slide_num: int, placeholder_name: str) -> dict[str, Any]:
    prs = Presentation(file_path)
    _slide, shape = _find_shape(prs, slide_num, placeholder_name)
    _require_text_frame(shape, slide_num, placeholder_name)
    return {"value": shape.text_frame.text}


def _write_placeholder(file_path: str, slide_num: int, placeholder_name: str, new_value: str) -> dict[str, Any]:
    backup_path = file_path + ".bak"
    shutil.copy2(file_path, backup_path)

    prs = Presentation(file_path)
    _slide, shape = _find_shape(prs, slide_num, placeholder_name)
    _require_text_frame(shape, slide_num, placeholder_name)

    text_frame = shape.text_frame
    previous_value = text_frame.text

    # Replace text inside the first paragraph's runs (not `.text =`) to
    # preserve run-level formatting/theme attributes.
    if text_frame.paragraphs and text_frame.paragraphs[0].runs:
        first_paragraph = text_frame.paragraphs[0]
        first_paragraph.runs[0].text = new_value
        for run in first_paragraph.runs[1:]:
            run.text = ""
    else:
        text_frame.text = new_value

    prs.save(file_path)
    return {
        "success": True,
        "slide": slide_num,
        "placeholder": placeholder_name,
        "previous_value": previous_value,
        "new_value": new_value,
        "backup": backup_path,
    }
