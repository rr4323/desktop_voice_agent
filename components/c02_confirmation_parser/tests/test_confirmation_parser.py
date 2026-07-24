"""Standalone tests for the Confirmation/Intent Parser (component 02).

Run in isolation: pytest components/c02_confirmation_parser
"""
import pytest

from components.c02_confirmation_parser.src.confirmation_parser import parse_confirmation


def test_parse_confirmation_stub_raises_until_implemented():
    """Placeholder so `pytest` collects something for this component.

    Replace with real cases from this component's README.md /
    docs/Component_IO_Spec.md section 2 as it's implemented.
    """
    with pytest.raises(NotImplementedError):
        parse_confirmation({})
