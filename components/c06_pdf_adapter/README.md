# 06. PDF Adapter

**Responsibility:** Extract text/table data from a PDF with page/element provenance. Read-only.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 6.

## Input

```json
{"file": "network_report.pdf", "query": "Q3 revenue total"}
```

## Output

```json
{
    "value": "2.4M",
    "provenance": {"file": "network_report.pdf", "page": 3, "element": "table_2/row_4/col_3"},
    "extraction_method": "text_layer"
}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c06_pdf_adapter
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

`pdfplumber`, `PyMuPDF`

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
