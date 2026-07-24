# 05. Policy Engine

**Responsibility:** The sole authority that decides whether a proposed action executes. Pure function, no model call.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 5.

## Input

```json
{
    "step_id": 2,
    "type": "write",
    "target": {"app": "xlsx", "file": "kpi_tracker.xlsx", "cell": "B7"},
    "current_cell_value": "1.8M"
}
```

## Output

```json
{
    "step_id": 2,
    "decision": "ASK_CONFIRM",
    "tier": "reversible-write-overwrite",
    "reason": "Target cell B7 already contains a non-empty value"
}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c05_policy_engine
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

_None — pure Python._

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
