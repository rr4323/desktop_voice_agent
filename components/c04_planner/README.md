# 04. Task Planner (LLM)

**Responsibility:** Convert a transcript + task context into a structured, schema-valid TaskPlan. Never executes anything itself.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 4.

## Input

```json
{
    "transcript": "pull the q3 revenue total from the network report and put it into the kpi tracker",
    "context": {"open_files": ["network_report.pdf", "kpi_tracker.xlsx"], "working_memory": {}}
}
```

## Output

```json
{
    "goal": "Copy Q3 revenue total from network_report.pdf into kpi_tracker.xlsx",
    "steps": [
        {"step_id": 1, "type": "read", "target": {"app": "pdf", "file": "network_report.pdf", "query": "Q3 revenue total"}},
        {"step_id": 2, "type": "write", "target": {"app": "xlsx", "file": "kpi_tracker.xlsx", "cell": "B7"}, "value_ref": "step_1.value", "depends_on": [1]}
    ]
}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c04_planner
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

`jsonschema`, `requests`

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
