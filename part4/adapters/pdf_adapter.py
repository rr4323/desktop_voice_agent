import logging

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

class PDFAdapter:
    """Read-only PDF adapter returning text and structured table data with provenance."""

    def __init__(self):
        if pdfplumber is None:
            raise ImportError("pdfplumber is required for PDFAdapter.")

    def extract_text_with_provenance(self, file_path: str) -> list:
        results = []
        extraction_method = "text_layer"

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # 1. Page text
                text = page.extract_text()
                if text:
                    results.append({
                        "value": text.strip(),
                        "provenance": {"file": file_path, "page": page_num, "element": "body_text"},
                        "extraction_method": extraction_method
                    })
                else:
                    logging.warning(f"Empty text layer on page {page_num}. Flagging OCR fallback.")
                    results.append({
                        "value": "",
                        "provenance": {"file": file_path, "page": page_num, "element": "body_text"},
                        "extraction_method": "ocr"
                    })

                # 2. Page tables
                tables = page.extract_tables()
                for table_idx, table in enumerate(tables, start=1):
                    for row_idx, row in enumerate(table, start=1):
                        for col_idx, cell in enumerate(row, start=1):
                            if cell:
                                results.append({
                                    "value": str(cell).strip(),
                                    "provenance": {
                                        "file": file_path,
                                        "page": page_num,
                                        "element": f"table_{table_idx}/row_{row_idx}/col_{col_idx}"
                                    },
                                    "extraction_method": extraction_method
                                })
        return results