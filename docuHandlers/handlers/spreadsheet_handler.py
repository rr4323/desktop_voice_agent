"""
Merges extracted metrics into an existing spreadsheet.

Rule: match by row label (metric name), not by position — the sheet's
existing structure is the source of truth. If a metric has no matching
row, it goes into an "unmatched" list for the diff preview rather than
being silently appended somewhere arbitrary.
"""
import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
import re


def _normalize_label(label: str) -> str:
    # "Revenue ($M)" -> "revenue" ; "Operating Margin (%)" -> "operating margin"
    return re.sub(r"\(.*?\)", "", label).strip().lower()


def merge_into_spreadsheet(xlsx_path: str, metrics: list, period: str, sheet_name: str = None) -> dict:
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb[sheet_name] if sheet_name else wb.active

    # Build a lookup of existing row labels -> row index (assumes col A = labels, row 1 = header)
    label_to_row = {}
    for row in range(2, ws.max_row + 1):
        cell_val = ws.cell(row=row, column=1).value
        if cell_val:
            label_to_row[_normalize_label(str(cell_val))] = row

    new_col = ws.max_column + 1
    header_cell = ws.cell(row=1, column=new_col, value=f"{period}")
    header_cell.font = Font(bold=True)

    matched, unmatched = [], []
    for m in metrics:
        key = _normalize_label(m["metric"])
        if key in label_to_row:
            row = label_to_row[key]
            # Convert % values to the fraction the sheet already uses if the
            # existing column stores fractions (openpyxl can't tell us the
            # user's intended display, so match the existing row's format).
            value = m["value"]
            existing_sample = ws.cell(row=row, column=2).value
            if m["unit"] == "%" and isinstance(existing_sample, (int, float)) and existing_sample < 1:
                value = value / 100.0
            ws.cell(row=row, column=new_col, value=value)
            matched.append({"metric": m["metric"], "row": row, "value": value})
        else:
            unmatched.append(m["metric"])

    out_path = xlsx_path.replace(".xlsx", "_updated.xlsx")
    wb.save(out_path)

    return {
        "output_path": out_path,
        "new_column": get_column_letter(new_col),
        "matched": matched,
        "unmatched": unmatched,
    }


if __name__ == "__main__":
    import sys, json
    sys.path.insert(0, "/home/claude/pipeline")
    from extractors.pdf_extractor import extract_financials

    extraction = extract_financials("/home/claude/pipeline/samples/q3_earnings.pdf")
    result = merge_into_spreadsheet(
        "/home/claude/pipeline/samples/financials.xlsx",
        extraction["metrics"],
        extraction["period"],
    )
    print(json.dumps(result, indent=2))
