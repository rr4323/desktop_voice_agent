# 16. LibreOffice Adapter

**Responsibility:** Convert a document to another format using headless
LibreOffice (`soffice --headless --convert-to`) — for cases the
native-library adapters (`c06_pdf_adapter`, `c07_xlsx_adapter`,
`c08_pptx_adapter`) can't handle directly: legacy formats they don't
read/write at all (`.doc`, `.xls`, `.ppt`), or producing a PDF from an
XLSX/PPTX for distribution.

This is a **completely different mechanism** from the accessibility adapter
(`c14`) — no GUI, no display, no accessibility tree. It drives
LibreOffice's own batch conversion engine directly, not its UI. Came out of
exploring `soffice`'s CLI options (`man libreoffice`) while debugging why
the GUI wouldn't render for `c14`'s manual test — headless mode sidesteps
that problem entirely because it never opens a window in the first place.

Still a **secondary path**: prefer `openpyxl`/`python-pptx`/`pdfplumber`
directly whenever the format is one they already handle. Reach for this
adapter for the formats/operations they don't cover.

## Input

```json
{"file": "network_report.doc", "target_format": "pdf"}
```

Optional: `filter_name` (e.g. `"writer_pdf_Export"`, for export-option
control — see `man libreoffice`'s `--convert-to` examples), `output_dir`
(defaults to the input file's own directory), `timeout_seconds` (default 60).

## Output

```json
{
    "success": true,
    "input_file": "network_report.doc",
    "output_file": "network_report.pdf",
    "target_format": "pdf"
}
```

Missing input file raises `FileNotFoundError` before ever invoking
`soffice`. A failed/unsupported conversion raises `RuntimeError` with
`soffice`'s own stderr/stdout attached. If `soffice` exits `0` but produces
no output file (happens on some malformed inputs), that's also treated as a
failure — the postcondition (the output file actually exists) is checked
explicitly rather than trusting the exit code, same principle as the
Verification component (`c10`).

## Implementation notes

- Each call runs with a **dedicated, throwaway `UserInstallation` profile
  directory** (via `-env:UserInstallation=file://...`, cleaned up after).
  Without this, LibreOffice's single-instance profile lock means a
  conversion can silently hang or fail if another `soffice` process —
  headless or GUI — happens to be running under the same user profile.
- Strips `LD_LIBRARY_PATH` from the subprocess environment (nothing else).
  On this dev box, a snap-packaged app leaks an `LD_LIBRARY_PATH` that
  shadows `soffice.bin`'s own `libstdc++`/`libpthread` with incompatible
  snap-core versions, causing a symbol lookup error at startup. Stripping
  just that one variable (not the whole environment, so `HOME`/`PATH`/
  locale are untouched) fixes it without side effects elsewhere.

## Standalone test

```bash
pytest components/c16_libreoffice_adapter
```

Converts `fixtures/sample.txt` to PDF and checks the real output: correct
path, non-zero size, and a genuine `%PDF-` magic-byte header — not just
"the process exited 0." Also covers an `output_dir` override landing the
file in the right place instead of next to the input, a missing input file
raising a clean error, and a bogus target format raising `RuntimeError`
rather than silently producing nothing.

## Dependencies

`soffice` (LibreOffice) installed on the system — no pip package involved.
