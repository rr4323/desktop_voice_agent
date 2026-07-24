"""Confirmation/Intent Parser (component 02): deterministic yes/no parsing.

Responsibility: parse a spoken response to a confirmation prompt into a
strict decision. Contract: docs/Component_IO_Spec.md, section 2.

Deliberately *not* an LLM call — this sits right next to the Policy Engine
as one of the few things allowed to unlock a consequential action, so the
same transcript must always produce the same decision (TDD §6.3's
determinism requirement applies here just as much as to the policy engine
itself). Pure string matching only.
"""
import re
from typing import Any

_AFFIRMATIVE_PATTERNS = [
    r"\byes\b", r"\byeah\b", r"\byep\b", r"\byup\b", r"\bsure\b",
    r"\bgo ahead\b", r"\bdo it\b", r"\bconfirm(ed)?\b", r"\bproceed\b",
    r"\bcorrect\b", r"\baffirmative\b", r"\bok(ay)?\b", r"\bplease do\b",
    r"\bsounds good\b",
]
_NEGATIVE_PATTERNS = [
    r"\bno\b", r"\bnope\b", r"\bnah\b", r"\bdon'?t\b", r"\bstop\b",
    r"\bcancel\b", r"\bnegative\b", r"\bwait\b", r"\bhold on\b",
]
# Phrases that negate a nearby affirmative word (e.g. "sure" in "not sure"
# means the opposite of "sure" alone) — these suppress an affirmative match
# rather than counting as one themselves, since "not sure" is uncertainty,
# not a confident no.
_HEDGE_PATTERNS = [r"\bnot sure\b", r"\bnot certain\b", r"\bnot really\b", r"\bi don'?t know\b"]

_AFFIRMATIVE_RE = re.compile("|".join(_AFFIRMATIVE_PATTERNS))
_NEGATIVE_RE = re.compile("|".join(_NEGATIVE_PATTERNS))
_HEDGE_RE = re.compile("|".join(_HEDGE_PATTERNS))


def parse_confirmation(request: dict[str, Any]) -> dict[str, Any]:
    """Parse request["transcript"] into a strict confirm/deny/reprompt decision."""
    transcript = request["transcript"].strip().lower()

    is_affirmative = bool(_AFFIRMATIVE_RE.search(transcript)) and not _HEDGE_RE.search(transcript)
    is_negative = bool(_NEGATIVE_RE.search(transcript))

    # Mixed or absent signals are treated the same as no match at all —
    # guessing on a confirmation that gates a real write/delete is worse
    # than asking again (same "clarify rather than guess" principle as the
    # ASR's low-confidence spans and the planner's `clarify` action).
    if is_affirmative and not is_negative:
        return {"confirmed": True, "match_rule": "affirmative_phrase"}
    if is_negative and not is_affirmative:
        return {"confirmed": False, "match_rule": "negative_phrase"}
    return {"confirmed": False, "match_rule": "no_match", "needs_reprompt": True}
