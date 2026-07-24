"""Persistent, multi-step browser session for the browser agent.

Unlike c15_browser_adapter.read_or_write (which deliberately opens and
closes a fresh browser per call for a single, predetermined action), an
autonomous agent needs one browser/page that stays open across many tool
calls while it figures out the next step for itself. This is a separate,
small implementation rather than an import from c15 — components in this
repo don't call into each other's code, only exchange JSON, so each keeps
its own copy of what it needs.
"""
import json
from typing import Any

from playwright.sync_api import sync_playwright

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# The web equivalent of the "role"-based element search in c14's
# accessibility adapter: anything a person could plausibly click, type
# into, or read as a result.
_INTERACTIVE_SELECTOR = (
    "a, button, input, textarea, select, "
    "[role=button], [role=link], [role=searchbox], [role=textbox]"
)

_DESCRIBE_JS = """(els) => els.map((el) => ({
    tag: el.tagName.toLowerCase(),
    type: el.getAttribute('type') || '',
    name: el.getAttribute('name') || '',
    id: el.getAttribute('id') || '',
    placeholder: el.getAttribute('placeholder') || '',
    aria_label: el.getAttribute('aria-label') || '',
    text: (el.innerText || el.value || '').trim().slice(0, 80),
    visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
}))"""


class BrowserSession:
    """One browser + one page, kept alive across an agent's tool calls."""

    def __init__(self, headless: bool = True):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=headless)
        self._page = self._browser.new_page(user_agent=_DEFAULT_USER_AGENT, locale="en-US")

    def navigate(self, url: str) -> str:
        self._page.goto(url, wait_until="domcontentloaded")
        self._page.wait_for_timeout(1000)
        return self.describe_page()

    def describe_page(self, max_elements: int = 40) -> str:
        """Return a compact, LLM-readable JSON summary of the current page:
        title, URL, and a numbered list of visible interactive elements
        with a usable selector for each. This is what lets the agent decide
        what to click/fill next on a page it's never seen before, the same
        way c14's role-based search lets it find an unnamed desktop widget.
        """
        raw_elements = self._page.eval_on_selector_all(_INTERACTIVE_SELECTOR, _DESCRIBE_JS)
        visible = [el for el in raw_elements if el["visible"]][:max_elements]
        for i, el in enumerate(visible):
            el["index"] = i
            el["selector"] = self._build_selector(el)
            del el["visible"]

        summary = {
            "url": self._page.url,
            "title": self._page.title(),
            "interactive_elements": visible,
        }
        return json.dumps(summary, indent=2)

    @staticmethod
    def _build_selector(el: dict[str, Any]) -> str:
        tag = el["tag"]
        if el["id"]:
            return f"#{el['id']}"
        if el["name"]:
            return f'{tag}[name="{el["name"]}"]'
        if el["aria_label"]:
            return f'{tag}[aria-label="{el["aria_label"]}"]'
        if el["text"]:
            safe_text = el["text"][:40].replace('"', "'")
            return f'{tag}:has-text("{safe_text}")'
        return f"{tag} >> nth={el['index']}"

    def click(self, selector: str) -> str:
        self._page.locator(selector).first.click(timeout=8000)
        self._page.wait_for_timeout(800)
        return self.describe_page()

    def fill(self, selector: str, value: str) -> str:
        self._page.locator(selector).first.fill(value, timeout=8000)
        return f"Filled {selector!r} with {value!r}"

    def press_key(self, selector: str, key: str) -> str:
        self._page.locator(selector).first.press(key, timeout=8000)
        self._page.wait_for_timeout(1000)
        return self.describe_page()

    def extract_text(self, selector: str = "body") -> str:
        return self._page.locator(selector).first.inner_text(timeout=8000)

    def screenshot(self, path: str) -> str:
        self._page.screenshot(path=path, full_page=True)
        return path

    def close(self) -> None:
        self._browser.close()
        self._playwright.stop()
