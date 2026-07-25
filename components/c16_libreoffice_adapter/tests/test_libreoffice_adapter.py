"""Standalone tests for the LibreOffice Adapter (component 16).

Run in isolation: pytest components/c16_libreoffice_adapter

Drives the real `soffice --headless` binary — no GUI, no display, no
AT-SPI, no other component needed. First run may be slower (LibreOffice's
first-time profile setup); subsequent runs are fast.
"""
import shutil

import pytest

from components.c16_libreoffice_adapter.src.libreoffice_adapter import convert

FIXTURE_TXT = __file__.replace("tests/test_libreoffice_adapter.py", "fixtures/sample.txt")


@pytest.fixture(autouse=True)
def check_soffice():
    if shutil.which("soffice") is None:
        pytest.skip("soffice (LibreOffice) binary not available in environment")


@pytest.fixture
def sample_txt(tmp_path):
    dest = tmp_path / "sample.txt"
    shutil.copy(FIXTURE_TXT, dest)
    return dest


def test_convert_txt_to_pdf_produces_valid_pdf(sample_txt):
    result = convert({"file": str(sample_txt), "target_format": "pdf"})

    assert result["success"] is True
    assert result["target_format"] == "pdf"
    assert result["output_file"] == str(sample_txt.with_suffix(".pdf"))

    output_path = sample_txt.with_suffix(".pdf")
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    with open(output_path, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_convert_respects_output_dir_override(sample_txt, tmp_path):
    output_dir = tmp_path / "converted"
    output_dir.mkdir()

    result = convert({"file": str(sample_txt), "target_format": "pdf", "output_dir": str(output_dir)})

    assert result["output_file"] == str(output_dir / "sample.pdf")
    assert (output_dir / "sample.pdf").exists()
    # nothing should have been dropped next to the input file itself
    assert not sample_txt.with_suffix(".pdf").exists()


def test_convert_missing_input_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError, match="input file not found"):
        convert({"file": str(tmp_path / "does_not_exist.txt"), "target_format": "pdf"})


def test_convert_bogus_target_format_raises_clean_error(sample_txt):
    with pytest.raises(RuntimeError):
        convert({"file": str(sample_txt), "target_format": "not_a_real_format"})
