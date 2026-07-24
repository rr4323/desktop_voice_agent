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

Find by accessible name (works for widgets that have one, e.g. a labeled entry):

```json
{"operation": "read", "app_name": "kpi_dashboard", "element_name": "revenue_field"}
```

Find by role instead — needed for apps whose main content area has **no**
accessible name at all. This is the common case, not the exception: neither
LibreOffice Writer's document canvas nor gedit's `GtkSourceView` expose a
name, only a role (`"document text"` / `"text"` respectively). When more
than one element matches, the adapter resolves to the **largest on-screen
match** — real apps can have other same-role elements that are hidden or
degenerate-sized (e.g. an unrealized popup entry), and the biggest visible
one is reliably the actual content area:

```json
{"operation": "write", "app_name": "gedit", "role": "text", "value": "my name is rajeev\n2026-07-24"}
```

`element_name` and `role` can be combined for extra precision; at least one
of the two is required.

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
`fixtures/accessible_test_app.py` (a minimal GTK window with a named entry,
a read-only label, and a tiny unnamed decoy entry — see below) inside that
isolated display and drives it via the real adapter — no mocking of the
accessibility tree.

Covers: reading a value with provenance, a write-then-read round trip,
writing to a read-only element raising a clean error, unknown app/element
name raising a clean `LookupError` rather than a raw AT-SPI/GLib exception,
role-only lookup resolving to the real element over a same-role decoy, and
a request with neither `element_name` nor `role` being rejected up front.

## Implementation notes

- Requires `python3-gi` + `gir1.2-atspi-2.0` + `at-spi2-core` from your OS
  package manager (see `requirements.txt` — this isn't pip-installable, it
  needs system GObject-introspection libraries), and a venv created with
  `--system-site-packages` so `import gi` resolves.
- Only handles text-valued elements (anything exposing the AT-SPI `Text` /
  `EditableText` interfaces — entries, text fields, labels). Non-text
  controls (checkboxes, sliders, etc.) aren't handled; extend
  `read_or_write` if a task needs one.
- **Verified against real gedit**, not just the GTK fixture app: launched
  gedit in an offscreen `Xvfb` session, used this exact `read_or_write` to
  write `"my name is rajeev"` + the date into its document (found by
  `role="text"`, correctly picking the real editor over an internal
  degenerate-sized decoy element gedit itself exposes), then drove the
  native GTK Save-As dialog via AT-SPI (`Atspi.Action.do_action` on the
  Save button, `EditableText` on the filename field) to save it to a real
  `.txt` file — confirmed by reading the file back off disk afterward.
  LibreOffice Writer was tried first and rejected as the demo target: its
  document canvas doesn't implement `EditableText` in a way AT-SPI can
  drive (a real, separate limitation from the role/name issue above).
- **LibreOffice Writer's canvas resists synthetic input entirely, not just
  `EditableText`.** Follow-up investigation (running a real window manager
  — `mutter`, already installed — in the offscreen session) confirmed the
  window itself renders correctly once a WM is present, and that real X
  keyboard focus does land on the LO Writer window (verified via
  `python-xlib`'s `get_input_focus()`, walking up to the named ancestor).
  Synthetic keyboard/mouse events (`Atspi.generate_keyboard_event`,
  `Atspi.generate_mouse_event`) were confirmed to work correctly against a
  plain GTK entry in the very same session, ruling out an environment or
  focus problem — yet those same events produce no effect on LO Writer's
  document. This points to something LO-specific in how its canvas
  processes input, not a fixable AT-SPI/window-manager configuration issue.
  **The correct fix for LibreOffice specifically is not more GUI
  automation** — it's LibreOffice's own UNO scripting API (`soffice
  --accept=...`, driven via `python-uno`), a genuinely different automation
  mechanism, the same way `c16`'s headless conversion is a different
  mechanism from this component. Not implemented here; flagging it as the
  known path if LO Writer read/write is needed later.

## Dependencies

`python3-gi`, `gir1.2-atspi-2.0`, `at-spi2-core` (system packages — see
`requirements.txt`).
