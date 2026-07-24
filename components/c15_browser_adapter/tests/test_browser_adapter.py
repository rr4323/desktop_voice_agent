"""Standalone tests for the Browser Adapter (component 15).

Run in isolation: pytest components/c15_browser_adapter

Drives a real (headless) Chromium against a local static fixture page
(fixtures/dashboard.html, loaded via file://) — no live network, no other
component needed.
"""
import os

import pytest

from components.c15_browser_adapter.src.browser_adapter import read_or_write

FIXTURE_URL = "file://" + os.path.join(os.path.dirname(__file__), "..", "fixtures", "dashboard.html")


def test_read_extracts_value_with_provenance():
    result = read_or_write({"operation": "read", "url": FIXTURE_URL, "selector": "#kpi-value"})

    assert result["value"] == "2.4M"
    assert result["provenance"] == {"url": FIXTURE_URL, "selector": "#kpi-value"}
    assert result["extraction_method"] == "browser_dom"


def test_write_reports_previous_and_new_value():
    write_result = read_or_write({
        "operation": "write", "url": FIXTURE_URL, "selector": "#note-field", "value": "2.4M",
    })
    assert write_result["success"] is True
    assert write_result["previous_value"] == "old note"
    assert write_result["new_value"] == "2.4M"


def test_write_does_not_persist_to_the_underlying_file():
    read_or_write({
        "operation": "write", "url": FIXTURE_URL, "selector": "#note-field", "value": "2.4M",
    })

    # Each call opens its own browser and reloads the URL fresh — a write
    # only mutates that call's live page, not the fixture file on disk (this
    # is the same statelessness as the other adapters' per-call open/close,
    # just worth asserting explicitly since "the page" isn't a file you'd
    # expect to obviously reset between calls).
    read_result = read_or_write({"operation": "read", "url": FIXTURE_URL, "selector": "#note-field"})
    assert read_result["value"] == "old note"


def test_write_to_non_fillable_element_raises_clean_error():
    with pytest.raises(ValueError, match="not a fillable form field"):
        read_or_write({
            "operation": "write", "url": FIXTURE_URL, "selector": "#static-label", "value": "x",
        })


def test_unknown_selector_raises_lookup_error():
    with pytest.raises(LookupError, match="no element matching selector"):
        read_or_write({
            "operation": "read", "url": FIXTURE_URL, "selector": "#does-not-exist", "timeout_ms": 1000,
        })
