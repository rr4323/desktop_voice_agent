# Shared schemas

These are the data structures components pass to each other (TDD §5.2 and
the per-component shapes in `Component_IO_Spec.md`). No component calls
another directly — they only exchange these JSON shapes. If you change one
of these, tell the other person: it's the contract both sides of the
pipeline depend on.

- `contracts.py` — plain-dataclass definitions of the core structures
  (`ActionRequest`, `PolicyDecision`, `ActionResult`, `AuditLogEntry`, ...),
  useful for type hints and quick validation.
- `examples/` — JSON fixtures of each shape, straight from the spec. Use
  these to stub out a component you depend on but haven't built yet.
