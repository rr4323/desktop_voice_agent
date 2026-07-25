"""PDF Adapter (component 06): extract text/table data from a PDF with
page/element provenance. Read-only.

Contract: docs/Component_IO_Spec.md, section 6.

Ported from the working prototype in part4/adapters/pdf_adapter.py (a
`PDFAdapter` class using pdfplumber for the text-layer/table path),
reshaped into this component's documented single-dict-in/single-dict-out
`extract` entry point, plus an OCR fallback for pages with no text layer
(scanned/image-only PDFs) using PyMuPDF's Tesseract-backed OCR text page —
this component's own requirements.txt already declares PyMuPDF for exactly
this. Degrades gracefully (empty value, extraction_method "ocr", low
confidence) if the `tesseract` binary isn't installed, rather than raising.
"""
import logging
from typing import Any

import pdfplumber

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - PyMuPDF is a required dependency
    fitz = None

logger = logging.getLogger(__name__)


def _ocr_page_text(file_path: str, page_num: int) -> str:
    """Best-effort OCR of one page via PyMuPDF+Tesseract. Returns "" if
    Tesseract isn't available rather than raising — the caller still tags
    the result extraction_method="ocr" so callers know text may be missing."""
    if fitz is None:
        return ""
    try:
        with fitz.open(file_path) as doc:
            page = doc[page_num - 1]
            textpage = page.get_textpage_ocr(full=True)
            return page.get_text(textpage=textpage).strip()
    except Exception:  # noqa: BLE001 - OCR is genuinely best-effort here
        logger.warning("OCR fallback unavailable/failed for %s page %d", file_path, page_num)
        return ""


def _extract_candidates(file_path: str) -> list[dict[str, Any]]:
    """Every (value, provenance, extraction_method, confidence) candidate
    on the page — body text plus every non-empty table cell."""
    candidates: list[dict[str, Any]] = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                candidates.append(
                    {
                        "value": text,
                        "provenance": {"file": file_path, "page": page_num, "element": "body_text"},
                        "extraction_method": "text_layer",
                        "confidence": 1.0,
                    }
                )
            else:
                ocr_text = _ocr_page_text(file_path, page_num)
                candidates.append(
                    {
                        "value": ocr_text,
                        "provenance": {"file": file_path, "page": page_num, "element": "body_text"},
                        "extraction_method": "ocr",
                        "confidence": 0.5 if ocr_text else 0.0,
                    }
                )

            for table_idx, table in enumerate(page.extract_tables(), start=1):
                for row_idx, row in enumerate(table, start=1):
                    for col_idx, cell in enumerate(row, start=1):
                        if not cell:
                            continue
                        candidates.append(
                            {
                                "value": str(cell).strip(),
                                "provenance": {
                                    "file": file_path,
                                    "page": page_num,
                                    "element": f"table_{table_idx}/row_{row_idx}/col_{col_idx}",
                                },
                                "extraction_method": "text_layer",
                                "confidence": 1.0,
                            }
                        )
    return candidates


def extract(request: dict[str, Any]) -> dict[str, Any]:
    """Extract the value matching request["query"] from request["file"].

    request: {"file": str, "query"?: str}
    If "query" is omitted, returns the first page's full body text.
    Raises LookupError if the file has no candidates matching the query.
    """
    file_path = request["file"]
    query = request.get("query")
    candidates = _extract_candidates(file_path)

    if query is None:
        for candidate in candidates:
            if candidate["provenance"]["element"] == "body_text":
                return candidate
        raise LookupError(f"no extractable text found in {file_path!r}")

    query_lower = query.lower()
    matches = [c for c in candidates if query_lower in c["value"].lower()]
    if not matches:
        query_words = [w for w in query_lower.split() if len(w) > 2]
        matches = [c for c in candidates if any(w in c["value"].lower() for w in query_words)]
    if not matches:
        raise LookupError(f"no content matching query {query!r} found in {file_path!r}")

    # Prefer the most specific match (a table cell) over a whole page of
    # body text when both matched — a table cell is the actual value the
    # caller almost certainly wants (e.g. "Q3 revenue total" -> "2.4M").
    table_matches = [m for m in matches if m["provenance"]["element"] != "body_text"]
    return table_matches[0] if table_matches else matches[0]
