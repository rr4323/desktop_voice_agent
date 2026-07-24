# 02. Confirmation/Intent Parser

**Responsibility:** Parse a spoken response to a confirmation prompt into a strict, deterministic decision.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 2.

## Input

```json
{"transcript": "yes go ahead"}
```

## Output

```json
{"confirmed": true, "match_rule": "affirmative_phrase"}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c02_confirmation_parser
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

_None — pure Python._

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
