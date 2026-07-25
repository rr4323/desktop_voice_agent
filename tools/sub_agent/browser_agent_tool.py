"""The `sub_agent` tool: wraps components/c17_browser_agent's autonomous
LangGraph ReAct browser agent behind the same Tool interface every other
adapter uses.

Registered under app name "browser_agent" — the planner reaches for this,
rather than tools/browser_tool.py (c15, one predetermined selector op),
for open-ended multi-step web tasks with no fixed selector, putting the
instruction in target["instruction"].

Safety note: c17_browser_agent does not route its own internal
navigate/click/fill actions through c05_policy_engine (see that
component's README) — this tool is the boundary where policy enforcement
happens instead. c05_policy_engine.evaluate() special-cases
target["app"] == "browser_agent" to always resolve ASK_CONFIRM
("autonomous-sub-agent" tier) for exactly this reason: by the time
execute_node calls this tool, the user has already confirmed launching an
autonomous sub-agent whose internal steps aren't individually gated.
"""
from typing import Any

from components.c17_browser_agent.src.browser_agent import run as run_browser_agent


class BrowserAgentTool:
    app_name = "browser_agent"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]
        print(target)
        instruction = target.get("instruction") or target.get("query")
        print(instruction)
        if not instruction:
            raise ValueError('browser_agent step requires target["instruction"]')

        outcome = run_browser_agent(
            instruction,
            headless=target.get("headless", True),
            model=target.get("model"),
            max_steps=target.get("max_steps"),
        )
        return {"success": True, "value": outcome["result"], "step_count": outcome["step_count"]}
