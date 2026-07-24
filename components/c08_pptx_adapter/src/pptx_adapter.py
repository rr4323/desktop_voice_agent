"""Stub implementation of the PPTX Adapter (component 08).

Responsibility: Read/write slide text, tables, and placeholders.
Contract: docs/Component_IO_Spec.md, section 8.
"""
from typing import Any


def read_or_write(request: dict[str, Any]) -> dict[str, Any]:
    """Implement per the input/output shapes in this component's README.md."""
    raise NotImplementedError("pptx_adapter.read_or_write not implemented yet")
