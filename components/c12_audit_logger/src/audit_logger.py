"""Audit Logger (component 12): write one structured, PII-masked log entry
per step.

Contract: docs/Component_IO_Spec.md, section 12.

Ported from the working prototype in part4/audit_logger.py (an
`AuditLogger` class), reshaped into this component's documented
single-dict-in/single-dict-out `log_entry` entry point. Masking covers two
sources, matching the IO spec's example: (1) `raw_fields` — the caller's
explicit "these are sensitive" payload (e.g. `{"msisdn": "..."}"`), always
masked; (2) a recursive scan of the visible entry (action/decision/result/
verification/transcript_snippet) for PII-named keys or inline phone-number
patterns, as a defensive second layer in case sensitive data leaks into a
field that wasn't explicitly flagged.
"""
import datetime
import json
import os
import re
from typing import Any

_PII_KEYS = {"msisdn", "cdr_id", "billing_account", "phone", "subscriber_id", "email"}
_PHONE_RE = re.compile(r"\b\d{7,15}\b")
_MASK = "***MASKED***"

_DEFAULT_LOG_PATH = os.environ.get("AUDIT_LOG_PATH", "audit.log")


def _mask_recursive(value: Any, masked_fields: set[str]) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, val in value.items():
            if str(key).lower() in _PII_KEYS:
                masked_fields.add(key)
                out[key] = _MASK
            else:
                out[key] = _mask_recursive(val, masked_fields)
        return out
    if isinstance(value, list):
        return [_mask_recursive(v, masked_fields) for v in value]
    if isinstance(value, str):
        masked, count = _PHONE_RE.subn(_MASK, value)
        if count:
            masked_fields.add("inline_phone")
        return masked
    return value


def log_entry(request: dict[str, Any]) -> dict[str, Any]:
    """Mask and append one audit entry; returns the entry actually written.

    request: {"transcript_snippet", "action", "decision", "confirmation",
              "result", "verification", "raw_fields"?, "log_path"?}
    """
    masked_fields: set[str] = set()

    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "transcript_snippet": _mask_recursive(request.get("transcript_snippet", ""), masked_fields),
        "action": _mask_recursive(request.get("action", {}), masked_fields),
        "decision": _mask_recursive(request.get("decision", {}), masked_fields),
        "confirmation": request.get("confirmation", ""),
        "result": _mask_recursive(request.get("result", ""), masked_fields),
        "verification": _mask_recursive(request.get("verification", ""), masked_fields),
    }

    # raw_fields is by definition sensitive (that's what the caller is
    # flagging it for) — mask it out of the emitted entry entirely and
    # record which field names were present, but never write the values.
    raw_fields = request.get("raw_fields") or {}
    masked_fields.update(raw_fields.keys())

    entry["masked_fields"] = sorted(masked_fields)

    log_path = request.get("log_path", _DEFAULT_LOG_PATH)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry
