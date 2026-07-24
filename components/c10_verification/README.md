# 10. Verification Module

**Responsibility:** Re-check that an executed action's postcondition actually holds, and flag implausible values.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 10.

## Input

```json
{
    "action_result": {"cell": "B7", "expected_value": "2.4M"},
    "current_read": {"cell": "B7", "value": "2.4M"},
    "historical_context": {"previous_quarter_value": "1.8M"}
}
```

## Output

```json
{"verified": true, "postcondition_met": true, "anomaly_flag": false}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c10_verification
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

_None — pure Python._

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
