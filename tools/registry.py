"""Tool registry: maps an ActionRequest's target["app"] to the Tool that
executes it.

The agent's execute node is the only caller of get_tool() — nothing here
decides *whether* a step should run; that's c05_policy_engine's job,
upstream of this dispatch (TDD §4).
"""
from typing import Any

from tools.accessibility_tool import AccessibilityTool
from tools.base import Tool
from tools.browser_tool import BrowserTool
from tools.compare_summarize_tool import CompareSummarizeTool
from tools.correct_document_tool import CorrectDocumentTool
from tools.docx_tool import DocxTool
from tools.libreoffice_tool import LibreOfficeTool
from tools.organize_files_tool import OrganizeFilesTool
from tools.pdf_tool import PDFTool
from tools.pdf_to_docx_tool import PdfToDocxTool
from tools.pptx_tool import PPTXTool
from tools.presentation_llm_tool import PresentationLLMTool
from tools.spreadsheet_merge_tool import SpreadsheetMergeTool
from tools.sub_agent.browser_agent_tool import BrowserAgentTool
from tools.xlsx_tool import XLSXTool

_TOOL_INSTANCES: list[Any] = [
    PDFTool(),
    XLSXTool(),
    PPTXTool(),
    DocxTool(),
    AccessibilityTool(),
    BrowserTool(),
    LibreOfficeTool(),
    OrganizeFilesTool(),
    CompareSummarizeTool(),
    CorrectDocumentTool(),
    PdfToDocxTool(),
    BrowserAgentTool(),
    PresentationLLMTool(),
    SpreadsheetMergeTool(),
]

TOOLS: dict[str, Tool] = {tool.app_name: tool for tool in _TOOL_INSTANCES}


def get_tool(app_name: str) -> Tool:
    try:
        return TOOLS[app_name]
    except KeyError:
        raise LookupError(f"no tool registered for app {app_name!r}; available: {sorted(TOOLS)}") from None
