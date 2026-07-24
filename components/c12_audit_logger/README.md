# 12. Audit Logger

**Responsibility:** Write one structured, PII-masked log entry per step.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 12.

## Input

```json
{
    "transcript_snippet": "update the kpi tracker with the q3 revenue total",
    "action": {"type": "write", "target": "kpi_tracker.xlsx!B7"},
    "decision": {"decision": "ASK_CONFIRM", "reason": "overwrite of existing value"},
    "confirmation": "user_approved",
    "result": "success",
    "verification": "pass",
    "raw_fields": {"msisdn": "491701234567"}
}
```

## Output

```json
{
    "timestamp": "2026-07-24T10:15:03Z",
    "transcript_snippet": "update the kpi tracker with the q3 revenue total",
    "action": {"type": "write", "target": "kpi_tracker.xlsx!B7"},
    "decision": {"decision": "ASK_CONFIRM", "reason": "overwrite of existing value"},
    "confirmation": "user_approved",
    "result": "success",
    "verification": "pass",
    "masked_fields": ["msisdn"]
}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c12_audit_logger
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

_None — pure Python._

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
