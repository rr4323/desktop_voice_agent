# 15. Browser Adapter

**Responsibility:** Read/write a value on a web page — e.g. pulling a KPI
off an internal ops dashboard, or filling a value into a web-based form —
using the same read/write-with-provenance shape as the PDF/XLSX/PPTX
adapters (`c06`-`c08`), so it plugs into the same `ActionRequest`/
`ActionResult` contract (`docs/TDD.md` §5.2) without the planner or policy
engine needing a special case for "it's a browser this time."

Added alongside the accessibility adapter (`c14`) to demonstrate the
hackathon brief's "operate the desktop using appropriate GUI, accessibility,
**browser**, or automation interfaces" requirement explicitly. Like `c14`,
this sits beside — not ahead of — the format-native adapters: use it when
the source of truth genuinely is a web page, not as a substitute for
reading a PDF/XLSX/PPTX file directly.

## Input

```json
{"operation": "read", "url": "https://ops-dashboard.internal/kpis", "selector": "#kpi-value"}
```
```json
{"operation": "write", "url": "https://ops-dashboard.internal/kpis", "selector": "#note-field", "value": "2.4M"}
```

## Output

```json
{
    "value": "2.4M",
    "provenance": {"url": "https://ops-dashboard.internal/kpis", "selector": "#kpi-value"},
    "extraction_method": "browser_dom"
}
```
```json
{"success": true, "selector": "#note-field", "previous_value": "1.8M", "new_value": "2.4M"}
```

Reading works against both plain elements (`inner_text`) and form fields
(`input_value`, tried first since inputs don't carry a text node). Writing
to a non-fillable element (e.g. a plain `<div>`) raises a clean `ValueError`
rather than failing silently. An unmatched selector raises a clean
`LookupError` rather than Playwright's default timeout stack trace.

## Standalone test

```bash
pytest components/c15_browser_adapter
```

Drives a real (headless) Chromium against a local static fixture page
(`fixtures/dashboard.html`, loaded via `file://`) — no live network, no
other component needed. Covers: reading a value with provenance, a write
reporting previous/new value, an explicit check that a write doesn't
persist back to the underlying file (each call opens its own page fresh —
worth asserting since that's less obvious than it is for a file-backed
adapter), writing to a non-fillable element, and an unmatched selector.

## Implementation notes

- Each call launches and closes its own headless Chromium instance —
  simple and stateless (matches the open/close-per-call shape of the
  XLSX/PPTX adapters), at the cost of a browser-launch overhead (~200-400ms)
  on every call. Fine for the current task volume; if that overhead ever
  matters, the obvious next step is a long-lived browser instance reused
  across calls.
- First use requires `python -m playwright install chromium` (downloads the
  browser binary, cached locally after that — no further network needed).

## Dependencies

`playwright` (plus its Chromium binary, downloaded via `playwright install`
— not a pip package, see above).
