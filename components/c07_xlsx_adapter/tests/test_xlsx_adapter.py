"""Standalone tests for the XLSX Adapter (component 07).

Run in isolation: pytest components/c07_xlsx_adapter
"""
import pytest

from components.c07_xlsx_adapter.src.xlsx_adapter import read_or_write


def test_read_or_write_stub_raises_until_implemented():
    """Placeholder so `pytest` collects something for this component.

    Replace with real cases from this component's README.md /
    docs/Component_IO_Spec.md section 7 as it's implemented.
    """
    with pytest.raises(NotImplementedError):
        read_or_write({})
