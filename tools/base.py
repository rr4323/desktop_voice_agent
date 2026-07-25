"""Common Tool interface every execution-adapter wrapper implements.

Kept intentionally thin: the agent's execute node only ever calls
`tool.run(step)`. No business logic lives here or in any individual tool
module — each tool just reshapes an ActionRequest-style step (TDD §5.2)
into the call its underlying component/adapter expects, and reshapes the
result back into an ActionResult-shaped dict. Whether a step is even
allowed to reach a tool is decided upstream, by c05_policy_engine — tools
don't re-check that.
"""
from typing import Any, Protocol


class Tool(Protocol):
    """`app_name` is the key the planner's `target["app"]` is matched
    against in tools/registry.py."""

    app_name: str

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        """Execute one ActionRequest-shaped step and return an
        ActionResult-shaped dict (a "value" for reads, a "success" +
        previous/new value for writes)."""
        ...
