"""Stub implementation of the PDF Adapter (component 06).

Responsibility: Extract text/table data from a PDF with page/element provenance. Read-only.
Contract: docs/Component_IO_Spec.md, section 6.
"""
from typing import Any


def extract(request: dict[str, Any]) -> dict[str, Any]:
    """Implement per the input/output shapes in this component's README.md."""
    raise NotImplementedError("pdf_adapter.extract not implemented yet")
