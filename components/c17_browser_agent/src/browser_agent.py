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

Fully local: the LLM runs via Ollama (no cloud API), per the TDD's
data-sovereignty requirement. Pull a tool-calling-capable model first:

    ollama pull qwen2.5:7b

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
import os
from typing import Any

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent

from components.c17_browser_agent.src.browser_session import BrowserSession

_DEFAULT_MODEL = "qwen2.5:7b"
_DEFAULT_BASE_URL = "http://localhost:11434"
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
"""


def _build_tools(session: BrowserSession, output_dir: str) -> list:
    @tool
    def navigate(url: str) -> str:
        """Go to a URL. Returns a JSON summary of the resulting page's
        title, url, and interactive_elements (each with a selector)."""
        return session.navigate(url)

    @tool
    def describe_page() -> str:
        """Return a JSON summary of the current page: title, url, and every
        visible interactive element (links, buttons, inputs) with a
        selector you can pass to click/fill/press_key."""
        return session.describe_page()

    @tool
    def click(selector: str) -> str:
        """Click the element matching `selector` (use one from a prior
        describe_page/navigate/click result). Returns the updated page
        summary."""
        return session.click(selector)

    @tool
    def fill(selector: str, value: str) -> str:
        """Type `value` into the input/textarea matching `selector`."""
        return session.fill(selector, value)

    @tool
    def press_key(selector: str, key: str) -> str:
        """Press a key (e.g. "Enter") while focused on the element matching
        `selector` — the usual way to submit a search box. Returns the
        updated page summary."""
        return session.press_key(selector, key)

    @tool
    def extract_text(selector: str = "body") -> str:
        """Return the visible text content of `selector` (default: the
        whole page body)."""
        return session.extract_text(selector)

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


def run(
    instruction: str,
    headless: bool = True,
    model: str | None = None,
    base_url: str | None = None,
    max_steps: int | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Complete `instruction` by autonomously driving a browser.

    All of model/base_url/max_steps/output_dir fall back to an env var
    (OLLAMA_MODEL / OLLAMA_BASE_URL / BROWSER_AGENT_MAX_STEPS /
    BROWSER_AGENT_OUTPUT_DIR) and then a hardcoded default, resolved at
    call time — so a caller (or a test) can override them per-run without
    needing to restart the process with different environment variables.

    Returns {"result": <final answer text>, "step_count": <int>}.
    """
    model = model or os.environ.get("OLLAMA_MODEL", _DEFAULT_MODEL)
    base_url = base_url or os.environ.get("OLLAMA_BASE_URL", _DEFAULT_BASE_URL)
    max_steps = max_steps or int(os.environ.get("BROWSER_AGENT_MAX_STEPS", _DEFAULT_MAX_STEPS))
    output_dir = output_dir or os.environ.get("BROWSER_AGENT_OUTPUT_DIR", _DEFAULT_OUTPUT_DIR)

    session = BrowserSession(headless=headless)
    try:
        tools = _build_tools(session, output_dir)
        llm = ChatOllama(model=model, base_url=base_url, temperature=0)
        agent = create_react_agent(llm, tools=tools, prompt=SYSTEM_PROMPT)

        try:
            result = agent.invoke(
                {"messages": [("user", instruction)]},
                config={"recursion_limit": max_steps * 2},  # each step is an (agent -> tools) pair of graph nodes
            )
        except GraphRecursionError:
            # Hitting the step budget without a final answer is an expected
            # outcome for an impossible/underspecified instruction, not a
            # crash — report it plainly instead of raising out of run().
            return {
                "result": f"Stopped after {max_steps} steps without reaching a final answer.",
                "step_count": max_steps * 2,
                "stopped_reason": "max_steps",
            }

        final_message = result["messages"][-1]
        return {
            "result": final_message.content,
            "step_count": len(result["messages"]),
        }
    finally:
        session.close()


if __name__ == "__main__":
    # Manual run:
    #   python -m components.c17_browser_agent.src.browser_agent "open bing, search for loop engineering, extract the results text, and save it to loop_engineering.txt"
    import sys

    outcome = run(" ".join(sys.argv[1:]))
    print(outcome["result"])
