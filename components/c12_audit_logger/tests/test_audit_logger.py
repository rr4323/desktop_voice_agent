"""Standalone tests for the Audit Logger (component 12).

Run in isolation: pytest components/c12_audit_logger
"""
import pytest

from components.c12_audit_logger.src.audit_logger import log_entry


def test_log_entry_stub_raises_until_implemented():
    """Placeholder so `pytest` collects something for this component.

    Replace with real cases from this component's README.md /
    docs/Component_IO_Spec.md section 12 as it's implemented.
    """
    with pytest.raises(NotImplementedError):
        log_entry({})
