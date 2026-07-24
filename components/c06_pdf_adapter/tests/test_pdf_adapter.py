"""Standalone tests for the PDF Adapter (component 06).

Run in isolation: pytest components/c06_pdf_adapter
"""
import pytest

from components.c06_pdf_adapter.src.pdf_adapter import extract


def test_extract_stub_raises_until_implemented():
    """Placeholder so `pytest` collects something for this component.

    Replace with real cases from this component's README.md /
    docs/Component_IO_Spec.md section 6 as it's implemented.
    """
    with pytest.raises(NotImplementedError):
        extract({})
