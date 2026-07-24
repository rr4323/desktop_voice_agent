# 09. Working Memory Store

**Responsibility:** Hold extracted values with provenance for the duration of a task, keyed by step ID.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 9.

## Input

```json
{"operation": "set", "key": "step_1.value", "value": "2.4M", "provenance": {"file": "network_report.pdf", "page": 3}}
```

## Output

```json
{"key": "step_1.value", "value": "2.4M", "provenance": {"file": "network_report.pdf", "page": 3}}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c09_working_memory
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

_None — pure Python._

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
