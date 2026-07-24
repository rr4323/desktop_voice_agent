"""
Confidence and safety gates — refuse or clarify when a task cannot be
completed safely or with sufficient confidence.
"""
import os


def check_file_exists(path: str, label: str = "File") -> dict:
    if not path or not os.path.exists(path):
        return {"decision": "refuse", "reason": f"{label} not found: {path}"}
    return {"decision": "go", "reason": f"{label} exists."}


def check_target_file(path: str, expected_ext: tuple) -> dict:
    if not os.path.exists(path):
        return {"decision": "refuse", "reason": f"Target file not found: {path}"}
    if not path.lower().endswith(expected_ext):
        return {"decision": "refuse", "reason": f"Target file is not one of {expected_ext}: {path}"}
    return {"decision": "go", "reason": "Target file exists and is the right type."}


def score_extraction(extraction: dict) -> dict:
    if extraction.get("period") is None:
        return {
            "decision": "clarify",
            "reason": "Could not identify which quarter/period this PDF covers.",
            "field_results": [],
        }

    field_results = []
    any_missing = False
    for m in extraction["metrics"]:
        if m["value"] is None:
            field_results.append({**m, "status": "clarify"})
            any_missing = True
        else:
            field_results.append({**m, "status": "go"})

    if any_missing:
        missing = [f["metric"] for f in field_results if f["status"] == "clarify"]
        return {
            "decision": "clarify",
            "reason": (
                f"Found the period ({extraction['period']}) but couldn't locate: "
                f"{', '.join(missing)}. Proceed with just the found fields, or point me to where these are?"
            ),
            "field_results": field_results,
        }

    return {
        "decision": "go",
        "reason": f"All {len(field_results)} metrics found for {extraction['period']} with numeric values.",
        "field_results": field_results,
    }


def gate_pdf_readable(pdf_path: str) -> dict:
    from extractors.pdf_extractor import has_text_layer

    if not os.path.exists(pdf_path):
        return {"decision": "refuse", "reason": f"PDF not found: {pdf_path}"}
    try:
        if not has_text_layer(pdf_path):
            return {
                "decision": "refuse",
                "reason": (
                    "This PDF has no text layer (likely scanned). Cannot extract safely "
                    "without OCR — refusing rather than guessing."
                ),
            }
    except Exception as e:
        return {"decision": "refuse", "reason": f"Cannot read PDF: {e}"}
    return {"decision": "go", "reason": "PDF has a readable text layer."}


def gate_text_extracted(extraction: dict, min_chars: int = 20) -> dict:
    text = (extraction.get("text") or "").strip()
    if extraction.get("error"):
        return {"decision": "refuse", "reason": extraction["error"]}
    if len(text) < min_chars:
        return {
            "decision": "refuse",
            "reason": "Source document has too little readable text to proceed safely.",
        }
    return {"decision": "go", "reason": f"Extracted {len(text)} characters of text."}


def gate_comparison_sources(sources: list[str], min_sources: int = 2) -> dict:
    if len(sources) < min_sources:
        return {"decision": "refuse", "reason": f"Need at least {min_sources} files to compare."}
    missing = [s for s in sources if not os.path.exists(s)]
    if missing:
        return {"decision": "refuse", "reason": f"Missing files: {', '.join(missing)}"}
    return {"decision": "go", "reason": f"{len(sources)} files ready for comparison."}


def gate_organise_instruction(prompt: str) -> dict:
    prompt_l = prompt.lower()
    known = ["type", "extension", "pdf", "spreadsheet", "document", "folder", "date"]
    if not any(k in prompt_l for k in known):
        return {
            "decision": "clarify",
            "reason": "Please specify how to organise (e.g. 'by file type' or 'into folders by extension').",
        }
    return {"decision": "go", "reason": "Organisation rule understood from prompt."}


def gate_document_corrections(corrections: list[dict]) -> dict:
    if not corrections:
        return {
            "decision": "clarify",
            "reason": "No corrections were detected. Specify typos to fix or pass --replacements old=new.",
        }
    low_conf = [c for c in corrections if c.get("confidence", 1.0) < 0.5]
    if len(low_conf) == len(corrections):
        return {
            "decision": "refuse",
            "reason": "All proposed corrections are low-confidence — refusing to modify the document.",
        }
    return {"decision": "go", "reason": f"{len(corrections)} correction(s) ready to apply."}
