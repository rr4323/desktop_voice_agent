"""Persistent, multi-step browser session for the browser agent.

Unlike c15_browser_adapter.read_or_write (which deliberately opens and
closes a fresh browser per call for a single, predetermined action), an
autonomous agent needs one browser/page that stays open across many tool
calls while it figures out the next step for itself. This is a separate,
small implementation rather than an import from c15 — components in this
repo don't call into each other's code, only exchange JSON, so each keeps
its own copy of what it needs.

Async, not sync, Playwright API: LangGraph's `create_react_agent` runs its
tool nodes as coroutines even when the overall graph is invoked via
`.ainvoke()` from a single thread — Playwright's *sync* API asserts every
call happens on the exact thread that started it, which broke the moment
a tool call landed on a different thread than `BrowserSession.__init__`
ran on ("Cannot switch to a different thread"). The async API has no such
constraint since everything runs on one event loop.
"""
import json
from typing import Any

from playwright.async_api import async_playwright

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
    text: (el.innerText || el.value || '').trim().slice(0, 50),
    visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
}))"""

# Groq's free-tier TPM limits (6000-8000 depending on model) are easily
# blown by a single page's worth of context — a search-results page can
# have dozens of links and thousands of characters of body text. These
# caps keep each tool result small enough that a few turns of accumulated
# conversation history still fit the budget.
_MAX_EXTRACT_CHARS = 4000


class BrowserSession:
    """One browser + one page, kept alive across an agent's tool calls.

    Construction is async (`await BrowserSession.create(...)`) since
    Playwright's async API has no sync constructor to call from `__init__`.
    """

    def __init__(self, playwright, browser, page):
        self._playwright = playwright
        self._browser = browser
        self._page = page

    @classmethod
    async def create(cls, headless: bool = True) -> "BrowserSession":
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=headless)
        page = await browser.new_page(user_agent=_DEFAULT_USER_AGENT, locale="en-US")
        return cls(playwright, browser, page)

    async def navigate(self, url: str) -> str:
        await self._page.goto(url, wait_until="domcontentloaded")
        await self._page.wait_for_timeout(1000)
        return await self.describe_page()

    async def describe_page(self, max_elements: int = 18) -> str:
        """Return a compact, LLM-readable JSON summary of the current page:
        title, URL, and a numbered list of visible interactive elements
        with a usable selector for each. This is what lets the agent decide
        what to click/fill next on a page it's never seen before, the same
        way c14's role-based search lets it find an unnamed desktop widget.
        """
        raw_elements = await self._page.eval_on_selector_all(_INTERACTIVE_SELECTOR, _DESCRIBE_JS)
        visible = [el for el in raw_elements if el["visible"]][:max_elements]
        for i, el in enumerate(visible):
            el["index"] = i
            el["selector"] = self._build_selector(el)
            del el["visible"]

        summary = {
            "url": self._page.url,
            "title": await self._page.title(),
            "interactive_elements": visible,
        }
        # No indent= here: pretty-printed whitespace burns real tokens
        # against Groq's free-tier per-minute budget for no benefit to the
        # model reading it.
        return json.dumps(summary, separators=(",", ":"))

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

    async def click(self, selector: str) -> str:
        await self._page.locator(selector).first.click(timeout=8000)
        await self._page.wait_for_timeout(800)
        return await self.describe_page()

    async def fill(self, selector: str, value: str) -> str:
        await self._page.locator(selector).first.fill(value, timeout=8000)
        return f"Filled {selector!r} with {value!r}"

    async def press_key(self, selector: str, key: str) -> str:
        await self._page.locator(selector).first.press(key, timeout=8000)
        await self._page.wait_for_timeout(1000)
        return await self.describe_page()

    async def extract_text(self, selector: str = "body") -> str:
        text = await self._page.locator(selector).first.inner_text(timeout=8000)
        if len(text) > _MAX_EXTRACT_CHARS:
            text = text[:_MAX_EXTRACT_CHARS] + f"\n...[truncated, {len(text)} chars total]"
        return text

    async def screenshot(self, path: str) -> str:
        await self._page.screenshot(path=path, full_page=True)
        return path

    async def close(self) -> None:
        await self._browser.close()
        await self._playwright.stop()
