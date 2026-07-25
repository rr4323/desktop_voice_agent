"""Browser Agent (component 17): natural-language instruction -> completed
browser task.

Given an instruction like "open bing, search loop engineering, save the
results to a file", this agent decides for itself which sequence of
navigate/describe_page/click/fill/press_key/extract_text/save_to_file calls
to make, via a LangGraph ReAct loop over a local Ollama model. Components
14/15/16 each execute one predetermined action per call; this is the
generic version — the thing a real c04_planner would drive step-by-step,
built directly here on top of a persistent browser session so it can be
tried standalone.

The LLM runs via the Groq API (a tool-calling-capable hosted model —
see GROQ_API_KEY / GROQ_MODEL below). Originally ran fully locally via
Ollama per the TDD's data-sovereignty goal (§6.2/§9); swapped for Groq's
hosted inference for speed/model quality.

IMPORTANT SAFETY NOTE: unlike the rest of this repo's pipeline, this agent
does NOT route its actions through the Policy Engine (c05) — it executes
every tool call it decides on directly and autonomously. That's a
deliberate scope choice for this standalone sub-agent, not an oversight,
but it means the safety guarantees described in the TDD (deterministic
ASK_CONFIRM/DENY gating before any consequential action) do not apply here.
Don't point this at anything where an unreviewed autonomous click/fill/
submit would matter — treat it as a research/demo component, not a drop-in
replacement for the gated pipeline.
"""
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent
from playwright.async_api import Error as PlaywrightError

from components.c17_browser_agent.src.browser_session import BrowserSession

_DEFAULT_MODEL = "openai/gpt-oss-120b"
_DEFAULT_MAX_STEPS = 15
_DEFAULT_OUTPUT_DIR = os.path.expanduser("~/browser_agent_output")

SYSTEM_PROMPT = """You are a browser automation agent. You complete the \
user's instruction by calling the tools available to you, one step at a \
time.

Rules:
- After `navigate` or `click`, you'll get back a JSON summary of the page \
  (title, url, interactive_elements). Use the "selector" field of the \
  relevant element for your next `click`/`fill`/`press_key` call — don't \
  guess selectors that weren't shown to you.
- Call `describe_page` again any time you're unsure what's currently on \
  the page.
- To submit a search box: `fill` it with the query, then `press_key` on \
  the same selector with key="Enter".
- Use `extract_text` to read the content the instruction asked for.
- If asked to save something to a file, call `save_to_file` and report the \
  exact path it returns back to the user in your final answer.
- When the instruction is fully satisfied, respond with a plain final \
  answer (no further tool call) summarizing what you did and found — \
  don't call a tool and also produce a final answer in the same turn.
- Only report content you actually saw via a tool result. Never invent \
  page content, search results, or file contents.
- If a tool reports "Error: ...", that action failed — don't treat it as \
  success. Try a different selector (call `describe_page` again if \
  needed), and if nothing works after a few attempts, give a final answer \
  explaining what you couldn't do rather than continuing to retry forever.
"""


def _build_tools(session: BrowserSession, output_dir: str) -> list:
    # Async, not sync — see browser_session.py's module docstring for why
    # (Playwright's sync API can't survive LangGraph dispatching tool calls
    # onto a different thread than the one that opened the browser).
    #
    # Each interactive tool catches PlaywrightError itself rather than
    # letting it propagate: LangGraph's ToolNode doesn't catch tool
    # exceptions by default, so an unhandled timeout (e.g. clicking a
    # selector that doesn't exist) would crash the whole agent run instead
    # of coming back as a normal "that didn't work" observation the model
    # can react to — which is what an autonomous, exploratory agent needs
    # for a bad selector or a slow-loading page to just be a retry, not a
    # crash.
    @tool
    async def navigate(url: str) -> str:
        """Go to a URL. Returns a JSON summary of the resulting page's
        title, url, and interactive_elements (each with a selector)."""
        try:
            return await session.navigate(url)
        except PlaywrightError as exc:
            return f"Error: could not navigate to {url!r}: {exc}"

    @tool
    async def describe_page() -> str:
        """Return a JSON summary of the current page: title, url, and every
        visible interactive element (links, buttons, inputs) with a
        selector you can pass to click/fill/press_key."""
        try:
            return await session.describe_page()
        except PlaywrightError as exc:
            return f"Error: could not read the current page: {exc}"

    @tool
    async def click(selector: str) -> str:
        """Click the element matching `selector` (use one from a prior
        describe_page/navigate/click result). Returns the updated page
        summary."""
        try:
            return await session.click(selector)
        except PlaywrightError as exc:
            return f"Error: could not click {selector!r}: {exc}"

    @tool
    async def fill(selector: str, value: str) -> str:
        """Type `value` into the input/textarea matching `selector`."""
        try:
            return await session.fill(selector, value)
        except PlaywrightError as exc:
            return f"Error: could not fill {selector!r}: {exc}"

    @tool
    async def press_key(selector: str, key: str) -> str:
        """Press a key (e.g. "Enter") while focused on the element matching
        `selector` — the usual way to submit a search box. Returns the
        updated page summary."""
        try:
            return await session.press_key(selector, key)
        except PlaywrightError as exc:
            return f"Error: could not press {key!r} on {selector!r}: {exc}"

    @tool
    async def extract_text(selector: str = "body") -> str:
        """Return the visible text content of `selector` (default: the
        whole page body)."""
        try:
            return await session.extract_text(selector)
        except PlaywrightError as exc:
            return f"Error: could not extract text from {selector!r}: {exc}"

    @tool
    def save_to_file(content: str, filename: str) -> str:
        """Save `content` to disk under `filename`. Returns the absolute
        path — always report this path back to the user when you use it."""
        os.makedirs(output_dir, exist_ok=True)
        safe_name = os.path.basename(filename)  # no path traversal
        path = os.path.join(output_dir, safe_name)
        with open(path, "w") as f:
            f.write(content)
        return path

    return [navigate, describe_page, click, fill, press_key, extract_text, save_to_file]


async def _run_async(
    instruction: str,
    headless: bool,
    model: str,
    api_key: str,
    max_steps: int,
    output_dir: str,
) -> dict[str, Any]:
    session = await BrowserSession.create(headless=headless)
    try:
        tools = _build_tools(session, output_dir)
        llm = ChatGroq(model=model, api_key=api_key, temperature=0)
        # checkpointer=False, not the default None: this runs as a node's
        # internal call from inside the outer graph's own Pregel.invoke(),
        # on the same thread — so without this, create_react_agent's "may
        # inherit the parent graph's checkpointer" default (see
        # langgraph's StateGraph.compile docstring) picks up the outer
        # graph's persistent SqliteSaver via ambient RunnableConfig
        # propagation, and then tries to use it from this coroutine's
        # ainvoke() — which fails, since SqliteSaver only supports sync
        # checkpoint methods ("The SqliteSaver does not support async
        # methods..."). This sub-agent doesn't want or need the outer
        # task's checkpoint persistence anyway (see module docstring: it's
        # a standalone, non-resumable run).
        agent = create_react_agent(llm, tools=tools, prompt=SYSTEM_PROMPT, checkpointer=False)

        try:
            # ainvoke, not invoke: the tools above are async def (Playwright's
            # async API — see the comment on _build_tools), and a StructuredTool
            # built from an async-only function can't be dispatched through the
            # sync invoke() path ("StructuredTool does not support sync
            # invocation").
            result = await agent.ainvoke(
                {"messages": [("user", instruction)]},
                config={"recursion_limit": max_steps * 5},  # each step is an (agent -> tools) pair of graph nodes
            )
        except GraphRecursionError:
            # Hitting the step budget without a final answer is an expected
            # outcome for an impossible/underspecified instruction, not a
            # crash — report it plainly instead of raising out of run().
            return {
                "result": f"Stopped after {max_steps} steps without reaching a final answer.",
                "step_count": max_steps * 5,
                "stopped_reason": "max_steps",
            }
        final_message = result["messages"][-1]
        return {
            "result": final_message.content,
            "step_count": len(result["messages"]),
        }
    finally:
        await session.close()


def run(
    instruction: str,
    headless: bool = True,
    model: str | None = None,
    api_key: str | None = None,
    max_steps: int | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Complete `instruction` by autonomously driving a browser.

    All of model/api_key/max_steps/output_dir fall back to an env var
    (GROQ_MODEL / GROQ_API_KEY / BROWSER_AGENT_MAX_STEPS /
    BROWSER_AGENT_OUTPUT_DIR) and then a hardcoded default, resolved at
    call time — so a caller (or a test) can override them per-run without
    needing to restart the process with different environment variables.

    Sync on the outside — so existing callers — tools/sub_agent/
    browser_agent_tool.py, the CLI entry point below — don't need to
    become async themselves; everything from here down to Playwright runs
    async internally, see browser_session.py's module docstring for why
    that matters (in particular, why it all has to run on one event loop).

    Normally drives that event loop itself via asyncio.run(). But
    asyncio.run() raises "cannot be called from a running event loop" if
    the calling thread already has one going (e.g. a caller that's
    itself async and invokes this from a sync context without offloading
    it first) — in that case, run the coroutine to completion on a
    dedicated worker thread instead, which gets its own fresh loop via
    the same asyncio.run(), and just block here until it's done. Either
    way this call doesn't return until the browser run has finished.

    Returns {"result": <final answer text>, "step_count": <int>}.
    """
    model = model or os.environ.get("GROQ_MODEL", _DEFAULT_MODEL)
    api_key = api_key or os.environ.get("GROQ_API_KEY")
    max_steps = max_steps or int(os.environ.get("BROWSER_AGENT_MAX_STEPS", _DEFAULT_MAX_STEPS))
    output_dir = output_dir or os.environ.get("BROWSER_AGENT_OUTPUT_DIR", _DEFAULT_OUTPUT_DIR)

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    coro = _run_async(instruction, headless, model, api_key, max_steps, output_dir)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


if __name__ == "__main__":
    # Manual run:
    #   python -m components.c17_browser_agent.src.browser_agent "open bing, search for loop engineering, extract the results text, and save it to loop_engineering.txt"
    import sys

    outcome = run(" ".join(sys.argv[1:]))
    print(outcome["result"])
