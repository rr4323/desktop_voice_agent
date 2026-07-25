"""Standalone tests for the PDF Adapter (component 06).

Run in isolation: pytest components/c06_pdf_adapter

Fixture PDFs are generated at test time with PyMuPDF (already a required
dependency of this component) instead of committing binary fixtures.
"""
import fitz
import pytest

from components.c06_pdf_adapter.src.pdf_adapter import extract


def _make_pdf(path: str, text: str | None) -> None:
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_extract_matches_query_in_text_layer(tmp_path):
    pdf_path = str(tmp_path / "network_report.pdf")
    _make_pdf(pdf_path, "Q3 Revenue Total: 2.4M")

    result = extract({"file": pdf_path, "query": "Revenue Total"})

    assert "2.4M" in result["value"]
    assert result["extraction_method"] == "text_layer"
    assert result["provenance"]["file"] == pdf_path
    assert result["provenance"]["page"] == 1


def test_extract_no_query_returns_full_first_page_text(tmp_path):
    pdf_path = str(tmp_path / "report.pdf")
    _make_pdf(pdf_path, "Whole page body text")

    result = extract({"file": pdf_path})

    assert "Whole page body text" in result["value"]
    assert result["provenance"]["element"] == "body_text"


def test_extract_raises_clean_error_when_query_not_found(tmp_path):
    pdf_path = str(tmp_path / "report.pdf")
    _make_pdf(pdf_path, "Nothing relevant here")

    with pytest.raises(LookupError):
        extract({"file": pdf_path, "query": "Q3 revenue total"})


def test_scanned_pdf_with_no_text_layer_falls_back_to_ocr_method(tmp_path):
    # No text inserted at all -> empty text layer, same shape as a
    # scanned/image-only PDF for pdfplumber's purposes.
    pdf_path = str(tmp_path / "scanned.pdf")
    _make_pdf(pdf_path, text=None)

    result = extract({"file": pdf_path})

    assert result["extraction_method"] == "ocr"
    assert result["confidence"] < 1.0
