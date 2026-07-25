"""Sanity tests for the tool registry: every tool imports cleanly and
registers under the app name execute_node will dispatch on."""
import pytest

from tools.registry import TOOLS, get_tool

EXPECTED_APPS = {
    "pdf",
    "xlsx",
    "pptx",
    "docx",
    "accessibility",
    "browser_adapter",
    "libreoffice",
    "organize_files",
    "compare_summarize",
    "correct_document",
    "pdf_to_docx",
    "browser_agent",
    "presentation_llm",
    "spreadsheet_merge",
}


def test_every_expected_app_is_registered():
    assert set(TOOLS.keys()) == EXPECTED_APPS


def test_get_tool_returns_matching_instance():
    for app_name in EXPECTED_APPS:
        tool = get_tool(app_name)
        assert tool.app_name == app_name


def test_get_tool_raises_clean_error_for_unknown_app():
    with pytest.raises(LookupError):
        get_tool("not_a_real_app")
