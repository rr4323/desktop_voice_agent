"""LibreOffice Adapter (component 16): headless document conversion.

Responsibility: convert a document to another format via
`soffice --headless --convert-to`, for cases the native-library adapters
(06-08) can't handle directly — legacy formats they don't read/write at all
(`.doc`, `.xls`, `.ppt`), or producing a PDF from an XLSX/PPTX for
distribution. No GUI, no accessibility tree — a completely different
automation mechanism from the accessibility adapter (14): this drives
LibreOffice's own batch conversion engine, not its UI.

Still a *secondary* path, same reasoning as 14/15: prefer openpyxl/
python-pptx/pdfplumber directly whenever the format is one they already
handle — this adapter exists for the formats/operations they don't cover.
"""
import os
import shutil
import subprocess
import tempfile
from typing import Any

_DEFAULT_TIMEOUT_SECONDS = 60


def convert(request: dict[str, Any]) -> dict[str, Any]:
    """Convert request["file"] to request["target_format"].

    request: {
        "file": "network_report.doc",
        "target_format": "pdf",
        "filter_name"?: "writer_pdf_Export",   # optional, for export-option control
        "output_dir"?: "...",                   # defaults to the input file's own directory
        "timeout_seconds"?: 60,
    }
    """
    if shutil.which("soffice") is None:
        raise RuntimeError("soffice (LibreOffice) not found on PATH")

    input_file = request["file"]
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"input file not found: {input_file}")

    target_format = request["target_format"]
    filter_name = request.get("filter_name")
    output_dir = request.get("output_dir") or os.path.dirname(os.path.abspath(input_file))
    timeout_seconds = request.get("timeout_seconds", _DEFAULT_TIMEOUT_SECONDS)

    convert_to_arg = f"{target_format}:{filter_name}" if filter_name else target_format

    input_stem = os.path.splitext(os.path.basename(input_file))[0]
    expected_output = os.path.join(output_dir, f"{input_stem}.{target_format}")

    # A dedicated, throwaway user profile per call avoids the well-known
    # LibreOffice single-instance profile lock — without this, a conversion
    # can silently hang or fail if another soffice process (headless or
    # GUI) is already running under the same user profile.
    profile_dir = tempfile.mkdtemp(prefix="soffice_profile_")
    try:
        # Snap-packaged apps on this kind of dev box can leak an
        # LD_LIBRARY_PATH that shadows soffice.bin's own libstdc++/libpthread
        # with incompatible snap-core versions, causing a symbol lookup
        # error. Stripping just this one variable (not the whole
        # environment) avoids that without losing HOME/PATH/locale, etc.
        env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}

        result = subprocess.run(
            [
                "soffice", "--headless", "--invisible", "--nologo", "--norestore",
                "--nofirststartwizard",
                f"-env:UserInstallation=file://{profile_dir}",
                "--convert-to", convert_to_arg,
                "--outdir", output_dir,
                input_file,
            ],
            env=env, capture_output=True, text=True, timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"soffice conversion of {input_file!r} timed out after {timeout_seconds}s") from exc
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"soffice conversion of {input_file!r} failed (exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )

    # soffice can exit 0 without actually producing output on some corrupt
    # or unsupported inputs — re-check the postcondition rather than
    # trusting the exit code alone (same principle as the Verification
    # component: confirm the effect actually landed).
    if not os.path.exists(expected_output):
        raise RuntimeError(
            f"soffice reported success but no output file was produced at {expected_output!r} "
            f"(stdout: {result.stdout.strip()!r})"
        )

    return {
        "success": True,
        "input_file": input_file,
        "output_file": expected_output,
        "target_format": target_format,
    }


if __name__ == "__main__":
    # Manual smoke test: python -m components.c16_libreoffice_adapter.src.libreoffice_adapter <file> <target_format>
    import json
    import sys

    print(json.dumps(convert({"file": sys.argv[1], "target_format": sys.argv[2]}), indent=2))
