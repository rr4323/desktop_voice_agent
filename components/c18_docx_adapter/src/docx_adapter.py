"""DOCX Adapter (component 18): read/write Word document paragraphs and
table cells.

Not part of the original 17-component spec — promoted from the working
prototype in part4/adapters/docx_adapter.py (a `DocxAdapter` class) into
its own component, following the pattern components 14-17 already used to
extend the spec. Reshaped into a single-dict-in/single-dict-out
`read_or_write` entry point to match every other adapter in this repo.
"""
import shutil
from typing import Any

from docx import Document


def read_or_write(request: dict[str, Any]) -> dict[str, Any]:
    """request: {"file", "operation": "read"|"write",
    "paragraph_index"? | ("table_index"?, "row"?, "col"?), "value"? (write only)}

    A read with neither paragraph_index nor table coordinates returns the
    whole document's paragraphs and table cells.
    """
    operation = request["operation"]
    file_path = request["file"]

    if operation == "create":
        return create(request)

    if operation == "read":
        if request.get("paragraph_index") is not None:
            return _read_paragraph(file_path, request["paragraph_index"])
        if request.get("table_index") is not None:
            return _read_table_cell(file_path, request["table_index"], request["row"], request["col"])
        return _read_document(file_path)

    if operation == "write":
        if request.get("paragraph_index") is not None:
            return _write_paragraph(file_path, request["paragraph_index"], request["value"])
        if request.get("table_index") is not None:
            return _write_table_cell(file_path, request["table_index"], request["row"], request["col"], request["value"])
        raise ValueError("write requires paragraph_index or table_index/row/col")

    raise ValueError(f"unknown operation: {operation!r}")


def create(request: dict[str, Any]) -> dict[str, Any]:
    """Build a brand-new document and save it to request["file"].

    request: {"file", "title"?, "paragraphs": [str, ...]}
    """
    file_path = request["file"]
    title = request.get("title")
    paragraphs = request.get("paragraphs") or []

    doc = Document()
    if title:
        doc.add_heading(title, level=1)
    for text in paragraphs:
        doc.add_paragraph(text)

    doc.save(file_path)
    return {"success": True, "file": file_path, "paragraph_count": len(paragraphs)}


def _read_document(file_path: str) -> dict[str, Any]:
    doc = Document(file_path)
    paragraphs = [{"index": i, "text": p.text} for i, p in enumerate(doc.paragraphs)]
    table_cells = [
        {"table_index": ti, "row": r, "col": c, "text": cell.text}
        for ti, table in enumerate(doc.tables)
        for r, row in enumerate(table.rows)
        for c, cell in enumerate(row.cells)
    ]
    return {"paragraphs": paragraphs, "table_cells": table_cells}


def _read_paragraph(file_path: str, paragraph_index: int) -> dict[str, Any]:
    doc = Document(file_path)
    try:
        return {"value": doc.paragraphs[paragraph_index].text}
    except IndexError as exc:
        raise IndexError(f"paragraph index {paragraph_index} out of range in {file_path!r}") from exc


def _read_table_cell(file_path: str, table_index: int, row: int, col: int) -> dict[str, Any]:
    doc = Document(file_path)
    try:
        return {"value": doc.tables[table_index].rows[row].cells[col].text}
    except IndexError as exc:
        raise IndexError(f"table cell ({table_index}, {row}, {col}) out of range in {file_path!r}") from exc


def _write_paragraph(file_path: str, paragraph_index: int, new_value: str) -> dict[str, Any]:
    backup_path = file_path + ".bak"
    shutil.copy2(file_path, backup_path)

    doc = Document(file_path)
    try:
        paragraph = doc.paragraphs[paragraph_index]
    except IndexError as exc:
        raise IndexError(f"paragraph index {paragraph_index} out of range in {file_path!r}") from exc

    previous_value = paragraph.text
    paragraph.text = new_value
    doc.save(file_path)
    return {
        "success": True,
        "paragraph_index": paragraph_index,
        "previous_value": previous_value,
        "new_value": new_value,
        "backup": backup_path,
    }


def _write_table_cell(file_path: str, table_index: int, row: int, col: int, new_value: str) -> dict[str, Any]:
    backup_path = file_path + ".bak"
    shutil.copy2(file_path, backup_path)

    doc = Document(file_path)
    try:
        cell = doc.tables[table_index].rows[row].cells[col]
    except IndexError as exc:
        raise IndexError(f"table cell ({table_index}, {row}, {col}) out of range in {file_path!r}") from exc

    previous_value = cell.text
    cell.text = new_value
    doc.save(file_path)
    return {
        "success": True,
        "table_index": table_index,
        "row": row,
        "col": col,
        "previous_value": previous_value,
        "new_value": new_value,
        "backup": backup_path,
    }
