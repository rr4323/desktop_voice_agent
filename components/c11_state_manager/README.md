# 11. State Manager

**Responsibility:** Track step status across a task; support pause, resume, correction, cancellation.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 11.

## Input

```json
{"operation": "update_status", "step_id": 2, "status": "done"}
```

## Output

```json
{"task_id": "t123", "steps": [{"step_id": 1, "status": "done"}, {"step_id": 2, "status": "paused"}]}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c11_state_manager
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

_None — pure Python._

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
