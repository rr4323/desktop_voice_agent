"""Stub implementation of the XLSX Adapter (component 07).

Responsibility: Read/write spreadsheet cells, formulas, and sheets.
Contract: docs/Component_IO_Spec.md, section 7.
"""
from typing import Any


def read_or_write(request: dict[str, Any]) -> dict[str, Any]:
    """Implement per the input/output shapes in this component's README.md."""
    raise NotImplementedError("xlsx_adapter.read_or_write not implemented yet")
