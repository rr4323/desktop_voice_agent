"""Tool wrapper around components/c14_accessibility_adapter.

Secondary path per the TDD (§6.4/§14) — reach for a file-format tool
first whenever there's a structured file to read/write directly.
"""
from typing import Any

from components.c14_accessibility_adapter.src.accessibility_adapter import read_or_write


class AccessibilityTool:
    app_name = "accessibility"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]
        operation = "write" if step.get("type") == "write" else "read"
        request = {
            "operation": operation,
            "app_name": target["app_name"],
            "element_name": target.get("element_name"),
            "role": target.get("role"),
        }
        if operation == "write":
            request["value"] = step.get("value")
        return read_or_write(request)
