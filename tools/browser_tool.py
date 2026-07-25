"""Tool wrapper around components/c15_browser_adapter: one predetermined
read/write against a known CSS selector. For open-ended multi-step web
tasks, see tools/sub_agent/browser_agent_tool.py instead.
"""
from typing import Any

from components.c15_browser_adapter.src.browser_adapter import read_or_write


class BrowserTool:
    app_name = "browser_adapter"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]
        operation = "write" if step.get("type") == "write" else "read"
        request = {"operation": operation, "url": target["url"], "selector": target["selector"]}
        if operation == "write":
            request["value"] = step.get("value")
        return read_or_write(request)
