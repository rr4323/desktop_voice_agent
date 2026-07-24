# 07. XLSX Adapter

**Responsibility:** Read/write spreadsheet cells, formulas, and sheets.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 7.

## Input

```json
{"file": "kpi_tracker.xlsx", "cell": "B7", "value": "2.4M", "operation": "write"}
```

## Output

```json
{"success": true, "cell": "B7", "previous_value": "1.8M", "new_value": "2.4M"}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c07_xlsx_adapter
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

`openpyxl`

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
