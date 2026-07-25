"""Policy Engine (component 05): deterministic ALLOW/ASK_CONFIRM/DENY authority.

Responsibility: the sole authority that decides whether a proposed action
executes. Pure function, no model call. Contract:
docs/Component_IO_Spec.md, section 5; full tier table: docs/TDD.md, §6.3.

Ported from the working prototype in part3/policy_engine.py (real logic
that predates this component's structure) and extended to cover every tier
the TDD table lists, plus one tier added for this refactor: any step
targeting the `browser_agent` sub-agent tool always requires confirmation
at this boundary, since that sub-agent does not gate its own internal
actions (see components/c17_browser_agent's README).
"""
from typing import Any

_DESTRUCTIVE_TYPES = {"delete", "clear"}

# Field names treated as subscriber PII per TDD §8 (MSISDN, CDR, billing).
_PII_KEYS = {"msisdn", "cdr_id", "billing_account", "phone", "subscriber_id", "email"}

# Phrases that mark a write as *asserting* a compliance/SLA status rather
# than reporting an extracted fact (TDD §6.3's "compliance-status assertion"
# tier) — the agent may report what it found, but not unilaterally decide
# the status.
_COMPLIANCE_KEYWORDS = {"breached", "not breached", "compliant", "non-compliant", "compliance_status", "sla_status"}

# Fragments that mark a proposed write as plausibly injected via untrusted
# document/webpage content rather than something the planner derived from
# the user's own speech (TDD §7). The policy engine denies these on its own
# merits regardless of *why* the planner proposed them.
_INJECTION_PATTERNS = ("ignore previous instructions", "delete all files", "rm -rf", "shell", "drop table")

_VALID_TYPES = {"read", "write", "create", "delete", "clear", "clarify"}


def evaluate(request: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one ActionRequest-shaped `request` and return a PolicyDecision.

    request: {"step_id", "type", "target", "current_cell_value"?, "value"?,
              "source"?, "user_independently_confirmed"?}
    """
    step_id = request.get("step_id")
    action_type = request.get("type")
    target = request.get("target") or {}
    current_cell_value = request.get("current_cell_value")
    value = request.get("value")
    source = request.get("source")

    def decision(decision: str, tier: str, reason: str, **extra: Any) -> dict[str, Any]:
        out = {"step_id": step_id, "decision": decision, "tier": tier, "reason": reason}
        out.update(extra)
        return out

    # 1. Untrusted-instruction-triggered: the action was requested by text
    #    found inside a document/webpage rather than the user's own speech.
    #    Denied unless the user has independently (re-)confirmed it by voice.
    if source == "untrusted_document" and not request.get("user_independently_confirmed"):
        return decision(
            "DENY",
            "untrusted-instruction-injection",
            "Action originates from untrusted document/webpage content, not the user's own speech",
        )

    # 2. Autonomous sub-agent boundary (browser_agent tool): its internal
    #    actions aren't individually policy-gated, so the entry point is.
    if target.get("app") == "browser_agent":
        return decision(
            "ASK_CONFIRM",
            "autonomous-sub-agent",
            "Step delegates to an autonomous browser sub-agent whose internal actions are not individually policy-gated",
        )

    # 2b. Bulk document-mutation tools (docuHandlers' presentation_llm,
    #     spreadsheet_merge): each edits many slides/cells in one call
    #     (an LLM-planned operations list, or every row a metrics list
    #     matches) rather than the single cell/placeholder the write-tier
    #     overwrite check below is designed to reason about — and, same as
    #     browser_agent, peek_current_value() can't cheaply read "the"
    #     current value of a whole document to feed that check anyway (see
    #     tools/presentation_llm_tool.py's/spreadsheet_merge_tool.py's own
    #     type == "read" guards).
    if target.get("app") in ("presentation_llm", "spreadsheet_merge"):
        return decision(
            "ASK_CONFIRM",
            "bulk-document-mutation",
            "Step performs a bulk, multi-part edit across an existing document rather than a single cell/slide write",
        )

    # 3. PII / subscriber data tier — checked before type-specific rules so
    #    it applies to reads and writes alike.
    if _touches_pii(target) or _touches_pii(value):
        return decision(
            "ASK_CONFIRM",
            "pii-subscriber-data",
            "Action touches subscriber PII (e.g. MSISDN, CDR, billing record)",
            mask=True,
        )

    if action_type not in _VALID_TYPES:
        return decision("DENY", "unknown-action", f"Unrecognized action type '{action_type}'")

    # 4. Compliance-status assertion tier.
    if action_type == "write" and _is_compliance_assertion(target, value):
        return decision(
            "ASK_CONFIRM",
            "compliance-status-assertion",
            "Write asserts a compliance/SLA status rather than reporting an extracted fact",
        )

    # 5. Read-only.
    if action_type == "read":
        return decision("ALLOW", "read-only", "Read-only operation on local file")

    # 6. Clarification requests from the planner pass straight through —
    #    there's no consequential action to authorize yet.
    if action_type == "clarify":
        return decision("ALLOW", "clarification-request", "Planner requested clarification; no action to authorize yet")

    # 7. Destructive.
    if action_type in _DESTRUCTIVE_TYPES:
        return decision("ASK_CONFIRM", "destructive", "Destructive file or content deletion requested")

    # 8. Write: injection guardrail, then overwrite-vs-empty.
    if action_type == "write":
        haystack = f"{value} {target}".lower()
        if any(pattern in haystack for pattern in _INJECTION_PATTERNS):
            return decision(
                "DENY",
                "untrusted-instruction-injection",
                "Action command derived from an untrusted/injurious pattern",
            )
        if current_cell_value is not None and str(current_cell_value).strip() != "":
            field = target.get("cell") or target.get("placeholder") or target.get("element") or "field"
            return decision(
                "ASK_CONFIRM",
                "reversible-write-overwrite",
                f"Target location '{field}' currently contains a non-empty value ({current_cell_value})",
            )
        return decision("ALLOW", "reversible-write-empty", "Target cell/field is empty")

    # 9. Create: a brand-new file is the safe default (nothing existing is
    #    touched); creating over a path that already has something there is
    #    an overwrite in disguise and gets the same confirmation write does.
    #    Reuses "current_cell_value" as a generic "does the target already
    #    have content" signal — agent/nodes/policy_check.py populates it via
    #    a file-existence check for create steps instead of a cell read.
    if action_type == "create":
        if current_cell_value:
            file_name = target.get("file") or "the target file"
            return decision(
                "ASK_CONFIRM",
                "create-overwrites-existing-file",
                f"'{file_name}' already exists — creating would overwrite it",
            )
        return decision("ALLOW", "create-new-file", "Target file does not exist yet")

    return decision("DENY", "unknown-action", f"Unrecognized action type '{action_type}'")


def _touches_pii(obj: Any) -> bool:
    if isinstance(obj, dict):
        if any(str(k).lower() in _PII_KEYS for k in obj):
            return True
        return any(_touches_pii(v) for v in obj.values())
    return False


def _is_compliance_assertion(target: dict[str, Any], value: Any) -> bool:
    haystack = f"{target.get('field', '')} {target.get('cell', '')} {target.get('placeholder', '')} {value}".lower()
    return any(keyword in haystack for keyword in _COMPLIANCE_KEYWORDS)
