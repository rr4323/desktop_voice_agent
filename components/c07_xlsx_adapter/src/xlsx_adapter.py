"""XLSX Adapter (component 07): read/write spreadsheet cells, formulas,
and sheets.

Contract: docs/Component_IO_Spec.md, section 7.

Ported from the working prototype in part4/adapters/xlsx_adapter.py (an
`XLSXAdapter` class), reshaped into this component's documented
single-dict-in/single-dict-out `read_or_write` entry point. Writes take a
`.bak` snapshot of the file before saving — a cheap, real rollback point
that lines up with the TDD's emphasis on reversible writes, and load
without `data_only` so untouched formula cells in the workbook are left
as formulas rather than getting flattened to their last-computed value.
"""
import csv
import os
import shutil
from typing import Any

import openpyxl


def _load_wb(file_path: str, data_only: bool = False):
    if file_path.endswith(".csv"):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                for row in reader:
                    ws.append(row)
        return wb
    return openpyxl.load_workbook(file_path, data_only=data_only)


def _save_wb(wb, file_path: str):
    if file_path.endswith(".csv"):
        ws = wb.active
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for row in ws.iter_rows(values_only=True):
                # Remove trailing empty cells if row is blank
                writer.writerow([cell if cell is not None else "" for cell in row])
    else:
        wb.save(file_path)


def read_or_write(request: dict[str, Any]) -> dict[str, Any]:
    """request: {"file", "cell", "sheet"?, "operation": "read"|"write", "value"? (write only)}

    "operation": "create" is a separate shape — see `create()` below — since
    it builds a brand-new workbook rather than addressing an existing cell.
    """
    operation = request["operation"]
    file_path = request["file"]

    if operation == "create":
        return create(request)

    cell_ref = request["cell"]
    sheet_name = request.get("sheet")

    if operation == "read":
        return _read_cell(file_path, sheet_name, cell_ref)
    if operation == "write":
        return _write_cell(file_path, sheet_name, cell_ref, request["value"])
    raise ValueError(f"unknown operation: {operation!r}")


def create(request: dict[str, Any]) -> dict[str, Any]:
    """Build a brand-new workbook and save it to request["file"].

    request: {"file", "sheet_name"?, "rows": [[cell, cell, ...], ...]}
    "rows" is written starting at A1, row by row.
    """
    file_path = request["file"]
    sheet_name = request.get("sheet_name")
    rows = request.get("rows") or []

    wb = openpyxl.Workbook()
    ws = wb.active
    if sheet_name:
        ws.title = sheet_name
    for row in rows:
        ws.append(row)

    _save_wb(wb, file_path)
    return {"success": True, "file": file_path, "sheet": ws.title, "row_count": len(rows)}


def _resolve_sheet(wb, sheet_name: str | None):
    if sheet_name and sheet_name in wb.sheetnames:
        return wb[sheet_name]
    return wb.active


def _read_cell(file_path: str, sheet_name: str | None, cell_ref: str) -> dict[str, Any]:
    wb = _load_wb(file_path, data_only=True)
    try:
        ws = _resolve_sheet(wb, sheet_name)
        try:
            value = ws[cell_ref].value
        except (ValueError, KeyError, IndexError) as exc:
            raise ValueError(f"invalid cell reference {cell_ref!r} in sheet {ws.title!r}") from exc
        return {"value": value, "cell": cell_ref, "sheet": ws.title}
    finally:
        wb.close()


def _write_cell(file_path: str, sheet_name: str | None, cell_ref: str, new_value: Any) -> dict[str, Any]:
    backup_path = file_path + ".bak"
    shutil.copy2(file_path, backup_path)

    wb = _load_wb(file_path)
    try:
        ws = _resolve_sheet(wb, sheet_name)
        try:
            previous_value = ws[cell_ref].value
            ws[cell_ref] = new_value
        except (ValueError, KeyError, IndexError) as exc:
            raise ValueError(f"invalid cell reference {cell_ref!r} in sheet {ws.title!r}") from exc
        _save_wb(wb, file_path)
        return {
            "success": True,
            "cell": cell_ref,
            "sheet": ws.title,
            "previous_value": previous_value,
            "new_value": new_value,
            "backup": backup_path,
        }
    finally:
        wb.close()
