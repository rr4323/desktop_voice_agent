"""Verification Module (component 10): re-check that an executed action's
postcondition actually holds, and flag implausible values.

Contract: docs/Component_IO_Spec.md, section 10.

This is a pure comparison function — per this component's own I/O spec
("Dependencies to mock: an adapter's read response — use fixtures"), it
never touches a file itself. The re-read through the actual adapter
happens one layer up (the agent's `verify` node calls the tool, then hands
the fresh `current_read` in here) — that keeps the same separation
part4/verification.py blurred (it called the adapter directly).

Anomaly detection (`detect_anomaly`) is ported as-is from
part4/verification.py: flags a KPI-style numeric write whose delta from
`historical_context` is implausible (TDD §6.7 / §11's churn-rate example)
even when the postcondition otherwise holds.
"""
from typing import Any

# Flag a numeric jump if it's more than 1000% relative change or the
# absolute delta exceeds 100,000 — same thresholds part4/verification.py
# used, kept here since they were tuned against the TDD's churn-rate demo
# case (§11: "churn rate jumping 40% ... anomaly_flag: true").
_RELATIVE_CHANGE_THRESHOLD = 10.0
_ABSOLUTE_DELTA_THRESHOLD = 100_000.0


def _is_number(v: Any) -> bool:
    try:
        float(str(v).replace("$", "").replace("%", "").replace(",", "").strip())
        return True
    except (TypeError, ValueError):
        return False


def _clean_number(v: Any) -> float:
    return float(str(v).replace("$", "").replace("%", "").replace(",", "").strip())


def _previous_from_context(historical_context: dict[str, Any] | None) -> Any:
    """Pull the comparison value out of a loosely-shaped historical_context.

    The field name isn't fixed by the spec (e.g. "previous_quarter_value"),
    so: prefer an explicit "previous_value" key, else fall back to the
    single value present when there's exactly one entry.
    """
    if not historical_context:
        return None
    if "previous_value" in historical_context:
        return historical_context["previous_value"]
    if len(historical_context) == 1:
        return next(iter(historical_context.values()))
    return None


def detect_anomaly(previous: Any, current: Any) -> bool:
    if previous is None or current is None:
        return False
    if not (_is_number(previous) and _is_number(current)):
        return False

    p = _clean_number(previous)
    c = _clean_number(current)

    if p == 0:
        return abs(c) > _ABSOLUTE_DELTA_THRESHOLD
    rel_change = abs((c - p) / p)
    return rel_change > _RELATIVE_CHANGE_THRESHOLD or abs(c - p) > _ABSOLUTE_DELTA_THRESHOLD


def verify(request: dict[str, Any]) -> dict[str, Any]:
    """Compare an action's expected postcondition against a fresh read.

    request: {"action_result": {..., "expected_value"}, "current_read": {..., "value"},
              "historical_context"?: {...}}
    """
    action_result = request.get("action_result") or {}
    current_read = request.get("current_read") or {}
    historical_context = request.get("historical_context")

    expected = action_result.get("expected_value")
    current = current_read.get("value")

    expected_str = str(expected).strip() if expected is not None else ""
    current_str = str(current).strip() if current is not None else ""
    postcondition_met = expected_str == current_str

    previous = _previous_from_context(historical_context)
    anomaly_flag = detect_anomaly(previous, current)

    return {
        "verified": postcondition_met,
        "postcondition_met": postcondition_met,
        "anomaly_flag": anomaly_flag,
    }
