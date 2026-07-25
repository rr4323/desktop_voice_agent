# 18. DOCX Adapter

**Responsibility:** Read/write Word document paragraphs and table cells.

Not part of the original 17-component spec — promoted from the working
prototype in `part4/adapters/docx_adapter.py` (built during the initial
merge, ahead of a dedicated component folder existing for it) into its own
component, following the same pattern components 14-17 used to extend the
original spec.

## Input

Whole-document read:
```json
{"file": "report.docx", "operation": "read"}
```
```json
{"paragraphs": [{"index": 0, "text": "..."}], "table_cells": [{"table_index": 0, "row": 0, "col": 0, "text": "..."}]}
```

Single paragraph write:
```json
{"file": "report.docx", "operation": "write", "paragraph_index": 2, "value": "New text"}
```
```json
{"success": true, "paragraph_index": 2, "previous_value": "Old text", "new_value": "New text"}
```

Single table cell write:
```json
{"file": "report.docx", "operation": "write", "table_index": 0, "row": 1, "col": 2, "value": "New text"}
```
```json
{"success": true, "table_index": 0, "row": 1, "col": 2, "previous_value": "Old text", "new_value": "New text"}
```

## Standalone test

```bash
pytest components/c18_docx_adapter
```

## Dependencies

`python-docx`
