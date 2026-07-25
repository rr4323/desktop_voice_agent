# 17. Browser Agent

**Responsibility:** Given a natural-language instruction, autonomously
drive a browser to complete it — the generic version of `c15_browser_adapter`.
Where `c15` executes one predetermined `{operation, url, selector}` action
per call, this component decides *for itself*, step by step, which
sequence of navigate/click/fill/extract actions to take, via a
[LangGraph](https://github.com/langchain-ai/langgraph) ReAct agent over a
tool-calling model hosted on [Groq](https://groq.com) (`langchain-groq`).

Conceptually this is what `c04_planner` would drive one `ActionRequest` at
a time in the full pipeline; here it's built as a self-contained loop so it
can be exercised standalone, per the request that kicked this off ("open
browser → open google → search X → get all text → save to file").

## ⚠️ Safety note — read before using

**This agent does not route through the Policy Engine (`c05`).** Every
tool call it decides on (`click`, `fill`, `save_to_file`, ...) executes
immediately and autonomously — there is no `ASK_CONFIRM`/`DENY` gate like
the rest of this repo's pipeline provides. That's a deliberate scope choice
for this standalone sub-agent, not an oversight, but it means none of the
TDD's deterministic safety guarantees apply here. Don't point it at
anything where an unreviewed autonomous click/fill/submit would matter —
treat it as a research/demo component, run in a throwaway browser context,
not a drop-in replacement for the gated pipeline.

## Setup

This needs a `GROQ_API_KEY` (see the repo root `.env`) — Groq's free tier
covers a **tool-calling-capable** model (`llama-3.3-70b-versatile` by
default):

```bash
pip install -r components/c17_browser_agent/requirements.txt
python -m playwright install chromium   # if c15/c17's Playwright browser isn't already installed
```

## Usage

```bash
python -m components.c17_browser_agent.src.browser_agent \
  "open bing, search for loop engineering, extract the results text, and save it to loop_engineering.txt"
```

Or from Python:

```python
from components.c17_browser_agent.src.browser_agent import run

outcome = run("open bing, search for loop engineering, save the results to loop_engineering.txt")
print(outcome["result"])       # the agent's final natural-language answer
print(outcome["step_count"])   # how many graph steps it took
```

`run()` accepts optional `model`, `api_key`, `max_steps`, and `output_dir`
overrides (each also configurable via `GROQ_MODEL`, `GROQ_API_KEY`,
`BROWSER_AGENT_MAX_STEPS`, `BROWSER_AGENT_OUTPUT_DIR` env vars) — resolved
at call time, not import time, so a single process can run several tasks
with different settings.

**Google will likely block it.** Headless Chromium hitting `google.com`
directly typically gets served Google's "unusual traffic" bot-detection
page instead of real results — this isn't a bug in the agent, it's Google's
bot detection working as intended. Bing (used in the example above) doesn't
do this for a normal, low-volume query. This was confirmed directly: an
earlier manual test against Google returned the block page verbatim; the
same query against Bing returned real results.

## Tools available to the agent

- `navigate(url)` — go to a URL; returns a JSON summary of the page.
- `describe_page()` — JSON summary of the current page: title, url, and
  every visible interactive element with a **selector** to use next. This
  is the web equivalent of `c14`'s AT-SPI role-based element search — it's
  how the agent finds things on a page it's never seen before, without
  needing hardcoded selectors.
- `click(selector)`, `fill(selector, value)`, `press_key(selector, key)` —
  standard interactions; each returns an updated page summary where
  relevant.
- `extract_text(selector="body")` — read visible text content.
- `save_to_file(content, filename)` — write to disk under
  `BROWSER_AGENT_OUTPUT_DIR` (default `~/browser_agent_output`); returns
  the absolute path.

## Standalone test

```bash
pytest components/c17_browser_agent
```

Skips cleanly if `GROQ_API_KEY` isn't set — this component was written to
be tested on a different machine than the one that wrote it, so don't be
surprised if it skips here. Covers: reading a
known value off the local `c15` fixture page and saving it to a file
(asserts the file's actual on-disk content, not just the agent's claim),
and that an impossible instruction terminates within the step budget
(`GraphRecursionError` from LangGraph is caught and turned into a clean
`{"stopped_reason": "max_steps"}` result) instead of raising or hanging.

## Implementation notes

- Uses its own `browser_session.py` (a persistent, multi-call Playwright
  wrapper) rather than importing `c15_browser_adapter`'s code — components
  in this repo don't call into each other, only exchange JSON, so this one
  keeps its own small copy of what it needs instead of breaking that rule.
  `c15`'s `read_or_write` deliberately opens/closes a browser per call for
  a single predetermined action; this agent needs one browser that stays
  open across many tool calls while it figures out the next step itself.
- `create_react_agent` (LangGraph's prebuilt ReAct loop) handles the
  agent↔tools loop; the system prompt instructs the model to keep calling
  tools until the instruction is satisfied, then respond with plain text
  (no further tool call) as its final answer, which is what ends the loop.

## Dependencies

`langchain`, `langchain-groq`, `langgraph`, `playwright` (plus a
`GROQ_API_KEY` — not a pip dependency).
