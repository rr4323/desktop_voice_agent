# 14. Accessibility Adapter

**Responsibility:** Read/write live desktop UI elements via the OS
accessibility tree (AT-SPI on Linux), for content the format-native
adapters (`c06_pdf_adapter`, `c07_xlsx_adapter`, `c08_pptx_adapter`) can't
resolve directly from a file — e.g. an embedded chart image, or visually
confirming a value in a running app window.

This turns TDD §6.4's "accessibility fallback" into its own component. It
demonstrates the hackathon brief's "operate the desktop using appropriate
GUI, accessibility, browser, or automation interfaces" requirement using a
real accessibility-tree round trip, rather than only file-format libraries.

**This is a secondary path, not a primary one.** Reading a PDF/XLSX/PPTX
file directly (components 06-08) is faster and strictly more deterministic
than driving a live GUI — there's no window to locate, no race with the
target app's UI thread, and the postcondition re-read (component 10,
Verification) is far more reliable against a file than against a live
accessibility tree. Reach for this adapter only when there's no structured
file to read/write.

## Input

```json
{"operation": "read", "app_name": "kpi_dashboard", "element_name": "revenue_field"}
```
```json
{"operation": "write", "app_name": "kpi_dashboard", "element_name": "revenue_field", "value": "2.4M"}
```

## Output

```json
{
    "value": "2.4M",
    "provenance": {"app": "kpi_dashboard", "element": "revenue_field", "role": "text"},
    "extraction_method": "accessibility_tree"
}
```
```json
{"success": true, "element": "revenue_field", "previous_value": "1.8M", "new_value": "2.4M"}
```

Writing to a non-editable element (no `EditableText` interface, e.g. a
plain label) raises a clean `ValueError` rather than failing silently —
same "report the limitation, don't fake success" principle as the PPTX
adapter's `unsupported_operation` case.

## Standalone test

```bash
pytest components/c14_accessibility_adapter
```

`tests/conftest.py` spins up a **throwaway, offscreen desktop** for the
whole test session — its own `Xvfb` display, its own D-Bus session bus, and
its own AT-SPI bus launcher — so these tests never touch whatever real
desktop session pytest happens to be running under. Each test then launches
`fixtures/accessible_test_app.py` (a minimal GTK window with one editable
entry and one read-only label, both with known accessible names) inside
that isolated display and drives it via the real adapter — no mocking of
the accessibility tree.

Covers: reading a value with provenance, a write-then-read round trip,
writing to a read-only element raising a clean error, and unknown
app/element name raising a clean `LookupError` rather than a raw AT-SPI/GLib
exception.

## Implementation notes

- Requires `python3-gi` + `gir1.2-atspi-2.0` + `at-spi2-core` from your OS
  package manager (see `requirements.txt` — this isn't pip-installable, it
  needs system GObject-introspection libraries), and a venv created with
  `--system-site-packages` so `import gi` resolves.
- Only handles text-valued elements (anything exposing the AT-SPI `Text` /
  `EditableText` interfaces — entries, text fields, labels). Non-text
  controls (checkboxes, sliders, etc.) aren't handled; extend
  `read_or_write` if a task needs one.

## Dependencies

`python3-gi`, `gir1.2-atspi-2.0`, `at-spi2-core` (system packages — see
`requirements.txt`).
