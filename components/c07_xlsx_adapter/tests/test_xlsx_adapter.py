"""Standalone tests for the XLSX Adapter (component 07).

Run in isolation: pytest components/c07_xlsx_adapter
"""
import openpyxl
import pytest

from components.c07_xlsx_adapter.src.xlsx_adapter import read_or_write


def _make_workbook(path: str) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws["B7"] = "1.8M"
    ws["C1"] = "=1+1"
    wb.save(path)


def test_write_then_read_round_trip(tmp_path):
    xlsx_path = str(tmp_path / "kpi_tracker.xlsx")
    _make_workbook(xlsx_path)

    write_result = read_or_write({"file": xlsx_path, "cell": "B7", "value": "2.4M", "operation": "write"})
    assert write_result == {
        "success": True,
        "cell": "B7",
        "sheet": "Sheet1",
        "previous_value": "1.8M",
        "new_value": "2.4M",
        "backup": xlsx_path + ".bak",
    }

    read_result = read_or_write({"file": xlsx_path, "cell": "B7", "operation": "read"})
    assert read_result["value"] == "2.4M"


def test_write_to_out_of_range_cell_errors_cleanly(tmp_path):
    xlsx_path = str(tmp_path / "kpi_tracker.xlsx")
    _make_workbook(xlsx_path)

    with pytest.raises(ValueError):
        read_or_write({"file": xlsx_path, "cell": "not_a_cell", "value": "x", "operation": "write"})


def test_write_preserves_formulas_in_other_cells(tmp_path):
    xlsx_path = str(tmp_path / "kpi_tracker.xlsx")
    _make_workbook(xlsx_path)

    read_or_write({"file": xlsx_path, "cell": "B7", "value": "2.4M", "operation": "write"})

    wb = openpyxl.load_workbook(xlsx_path)
    assert wb["Sheet1"]["C1"].value == "=1+1"


def test_unknown_operation_raises():
    with pytest.raises(ValueError):
        read_or_write({"file": "x.xlsx", "cell": "A1", "operation": "delete"})


def test_create_builds_a_new_workbook_with_rows(tmp_path):
    xlsx_path = str(tmp_path / "new_sheet.xlsx")

    result = read_or_write(
        {
            "file": xlsx_path,
            "operation": "create",
            "sheet_name": "Summary",
            "rows": [["Metric", "Value"], ["Revenue", "2.4M"]],
        }
    )

    assert result == {"success": True, "file": xlsx_path, "sheet": "Summary", "row_count": 2}

    wb = openpyxl.load_workbook(xlsx_path)
    assert wb.active.title == "Summary"
    assert wb.active["A1"].value == "Metric"
    assert wb.active["B2"].value == "2.4M"
