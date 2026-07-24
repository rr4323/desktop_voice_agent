# 08. PPTX Adapter

**Responsibility:** Read/write slide text, tables, and placeholders.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 8.

## Input

```json
{"file": "exec_briefing.pptx", "slide": 4, "placeholder": "churn_value", "value": "3.1%", "operation": "write"}
```

## Output

```json
{"success": true, "slide": 4, "placeholder": "churn_value", "previous_value": "2.9%", "new_value": "3.1%"}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c08_pptx_adapter
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

`python-pptx`

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
