import json
import datetime
import re

PII_KEYS = {"msisdn", "cdr_id", "billing_account", "phone", "subscriber_id", "email"}
PHONE_RE = re.compile(r"\b\d{7,15}\b")

def _mask_value(v):
    return "***MASKED***"

def _mask_text(s, masked_fields):
    if not isinstance(s, str):
        return s
    new_str, count = PHONE_RE.subn(_mask_value(""), s)
    if count > 0:
        masked_fields.append("inline_phone")
    return new_str

def _mask_payload(payload):
    masked_fields = []

    def _rec(v):
        if isinstance(v, dict):
            out = {}
            for k, val in v.items():
                if k.lower() in PII_KEYS:
                    masked_fields.append(k)
                    out[k] = _mask_value(val)
                else:
                    out[k] = _rec(val)
            return out
        elif isinstance(v, list):
            return [_rec(x) for x in v]
        elif isinstance(v, str):
            return _mask_text(v, masked_fields)
        else:
            return v

    return _rec(payload), list(set(masked_fields))

class AuditLogger:
    """Compliant audit logger generating structured JSON-lines logs with PII masking."""

    def __init__(self, path="audit.log"):
        self.path = path

    def write_entry(self, step_id: str, action: dict, decision: dict, result: dict, verification: dict, transcript: str = "", extra: dict = None):
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        
        raw_payload = {
            "timestamp": timestamp,
            "transcript_snippet": transcript,
            "step_id": step_id,
            "action": action,
            "decision": decision,
            "result": result,
            "verification": verification,
            "extra": extra or {}
        }

        masked_payload, masked_fields = _mask_payload(raw_payload)
        masked_payload["masked_fields"] = masked_fields

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(masked_payload, ensure_ascii=False) + "\n")

        return masked_payload