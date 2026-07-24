"""Browser Adapter (component 15): read/write a value on a web page.

Responsibility: extend the "automation interface" required capability to
the browser — e.g. reading a KPI off an internal ops dashboard, or filling
a value into a web-based form — using the same read/write-with-provenance
shape as the PDF/XLSX/PPTX adapters (06-08), so it plugs into the same
ActionRequest/ActionResult contract (docs/TDD.md §5.2) without the planner
or policy engine needing a special case for "it's a browser this time."

Like the accessibility adapter (14), this sits alongside — not ahead of —
the format-native adapters: use it when the source of truth genuinely is a
web page, not as a substitute for reading a PDF/XLSX/PPTX file directly.
"""
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

_DEFAULT_TIMEOUT_MS = 5000


def read_or_write(request: dict[str, Any]) -> dict[str, Any]:
    """Read or write a value at a CSS selector on a page.

    request (read):  {"operation": "read", "url": "...", "selector": "..."}
    request (write): {"operation": "write", "url": "...", "selector": "...", "value": "..."}
    """
    operation = request["operation"]
    url = request["url"]
    selector = request["selector"]
    timeout_ms = request.get("timeout_ms", _DEFAULT_TIMEOUT_MS)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url)
            locator = page.locator(selector)
            try:
                locator.wait_for(state="attached", timeout=timeout_ms)
            except PlaywrightError as exc:
                raise LookupError(f"no element matching selector {selector!r} found on {url!r}") from exc

            if operation == "read":
                try:
                    # Form fields store their content in the "value"
                    # property, not as text nodes — inner_text() reads back
                    # empty for an <input>/<textarea>.
                    value = locator.input_value()
                except PlaywrightError:
                    value = locator.inner_text()
                return {
                    "value": value,
                    "provenance": {"url": url, "selector": selector},
                    "extraction_method": "browser_dom",
                }

            if operation == "write":
                value = request["value"]
                try:
                    previous_value = locator.input_value()
                except PlaywrightError as exc:
                    raise ValueError(
                        f"element {selector!r} on {url!r} is not a fillable form field"
                    ) from exc
                locator.fill(value)
                new_value = locator.input_value()
                return {
                    "success": True,
                    "selector": selector,
                    "previous_value": previous_value,
                    "new_value": new_value,
                }

            raise ValueError(f"unknown operation: {operation!r}")
        finally:
            browser.close()


if __name__ == "__main__":
    # Manual smoke test: python -m components.c15_browser_adapter.src.browser_adapter <url> <selector> [value_to_write]
    import json
    import sys

    url_arg = sys.argv[1]
    selector_arg = sys.argv[2]
    if len(sys.argv) > 3:
        print(json.dumps(read_or_write({
            "operation": "write", "url": url_arg, "selector": selector_arg, "value": sys.argv[3],
        }), indent=2))
    else:
        print(json.dumps(read_or_write({
            "operation": "read", "url": url_arg, "selector": selector_arg,
        }), indent=2))
