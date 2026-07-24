# 13. Orchestrator

**Responsibility:** Wires all other components together per the data flow in the TDD. The only component that is an integration test, not a unit-testable leaf.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 13.

## Input

```json
{"transcript": "pull the q3 revenue total from the network report and put it into the kpi tracker"}
```

## Output

```json
{"task_id": "t123", "status": "done", "audit_trail": ["..."]}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c13_orchestrator
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

_None — pure Python._

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
