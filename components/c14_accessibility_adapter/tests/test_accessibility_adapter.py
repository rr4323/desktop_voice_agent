"""Standalone tests for the Accessibility Adapter (component 14).

Run in isolation: pytest components/c14_accessibility_adapter

conftest.py spins up a throwaway, offscreen Xvfb + D-Bus + AT-SPI stack for
these tests, then each test launches the fixture GTK app (fixtures/
accessible_test_app.py) and drives it via the real adapter — no mocking of
the accessibility tree itself.
"""
import pytest

from components.c14_accessibility_adapter.src.accessibility_adapter import read_or_write

APP_NAME = "accessible_test_app"


def test_read_returns_current_value_with_provenance(accessible_app):
    result = read_or_write({
        "operation": "read", "app_name": APP_NAME, "element_name": "kpi_value_entry",
    })

    assert result["value"] == "initial value"
    assert result["provenance"] == {"app": APP_NAME, "element": "kpi_value_entry", "role": "text"}
    assert result["extraction_method"] == "accessibility_tree"


def test_write_then_read_round_trips(accessible_app):
    write_result = read_or_write({
        "operation": "write", "app_name": APP_NAME,
        "element_name": "kpi_value_entry", "value": "2.4M",
    })
    assert write_result["success"] is True
    assert write_result["previous_value"] == "initial value"
    assert write_result["new_value"] == "2.4M"

    read_result = read_or_write({
        "operation": "read", "app_name": APP_NAME, "element_name": "kpi_value_entry",
    })
    assert read_result["value"] == "2.4M"


def test_write_to_readonly_element_raises_clean_error(accessible_app):
    with pytest.raises(ValueError, match="not editable"):
        read_or_write({
            "operation": "write", "app_name": APP_NAME,
            "element_name": "readonly_label", "value": "should fail",
        })


def test_unknown_app_raises_lookup_error(accessible_app):
    with pytest.raises(LookupError, match="no running app"):
        read_or_write({
            "operation": "read", "app_name": "no-such-app-anywhere",
            "element_name": "kpi_value_entry",
        })


def test_unknown_element_raises_lookup_error(accessible_app):
    with pytest.raises(LookupError, match="no accessible element"):
        read_or_write({
            "operation": "read", "app_name": APP_NAME, "element_name": "no-such-element",
        })
