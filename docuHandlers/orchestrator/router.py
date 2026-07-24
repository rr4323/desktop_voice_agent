"""Route classified intents to the appropriate handler pipeline."""
import os

from orchestrator.confidence_gate import (
    check_target_file,
    gate_comparison_sources,
    gate_document_corrections,
    gate_organise_instruction,
    gate_pdf_readable,
    gate_text_extracted,
    score_extraction,
)
from extractors.pdf_extractor import extract_financials
from handlers.spreadsheet_handler import merge_into_spreadsheet
from handlers.presentation_handler import update_presentation
from handlers.file_organizer import organise_files
from handlers.comparison_handler import compare_and_summarize
from handlers.document_corrector import correct_document
from handlers.document_handler import transfer_pdf_to_docx
from extractors.text_extractor import extract_text
from output.diff_preview import (
    build_spreadsheet_preview,
    build_presentation_preview,
    build_organise_preview,
    build_comparison_preview,
    build_correction_preview,
    build_document_update_preview,
)


def _resolve(path: str | None, working_dir: str) -> str | None:
    if not path:
        return None
    if os.path.isabs(path) and os.path.exists(path):
        return path
    if os.path.exists(path):
        return os.path.abspath(path)
    joined = os.path.join(working_dir, os.path.basename(path))
    if os.path.exists(joined):
        return joined
    if os.path.isabs(path):
        return path
    return os.path.join(working_dir, path)


def run_task(intent: dict, prompt: str, working_dir: str, replacements: list[str] | None = None) -> dict:
    log = []
    task = intent.get("new_task_type") or intent.get("task_type")

    if task == "pdf_to_spreadsheet":
        source = _resolve(intent["source_pdf"], working_dir)
        target = _resolve(intent["target_sheet"], working_dir)

        for stage, result in [
            ("confidence_gate_target", check_target_file(target, (".xlsx", ".csv"))),
            ("confidence_gate_pdf", gate_pdf_readable(source)),
        ]:
            log.append({"stage": stage, "result": result})
            if result["decision"] != "go":
                return {"status": result["decision"], "message": result["reason"], "log": log}

        extraction = extract_financials(source)
        log.append({"stage": "extraction", "result": extraction})

        gate = score_extraction(extraction)
        log.append({"stage": "confidence_gate_content", "result": gate})
        if gate["decision"] in ("clarify", "refuse"):
            return {"status": gate["decision"], "message": gate["reason"], "log": log}

        merge_result = merge_into_spreadsheet(target, extraction["metrics"], extraction["period"])
        log.append({"stage": "spreadsheet_handler", "result": merge_result})
        preview = build_spreadsheet_preview(
            merge_result, extraction["period"], os.path.basename(source), os.path.basename(target)
        )
        return {"status": "done", "preview": preview, "output_file": merge_result["output_path"], "log": log}

    if task == "pdf_to_doc":
        source = _resolve(intent["source_pdf"], working_dir)
        target = _resolve(intent["target_document"], working_dir)

        for stage, result in [
            ("confidence_gate_target", check_target_file(target, (".docx",))),
            ("confidence_gate_pdf", gate_pdf_readable(source)),
        ]:
            log.append({"stage": stage, "result": result})
            if result["decision"] != "go":
                return {"status": result["decision"], "message": result["reason"], "log": log}

        result = transfer_pdf_to_docx(source, target)
        log.append({"stage": "document_handler", "result": result})
        if not result["replacements"]:
            return {
                "status": "clarify",
                "message": (
                    "Document saved but no placeholders matched extracted PDF values."
                ),
                "output_file": result["output_path"],
                "log": log,
            }
        preview = build_document_update_preview(result)
        return {"status": "done", "preview": preview, "output_file": result["output_path"], "log": log}

    if task == "update_presentation":
        source = _resolve(intent["source_document"], working_dir)
        target = _resolve(intent["target_presentation"], working_dir)

        text_gate = gate_text_extracted(extract_text(source))
        log.append({"stage": "confidence_gate_source", "result": text_gate})
        if text_gate["decision"] != "go":
            return {"status": text_gate["decision"], "message": text_gate["reason"], "log": log}

        target_check = check_target_file(target, (".pptx",))
        log.append({"stage": "confidence_gate_target", "result": target_check})
        if target_check["decision"] != "go":
            return {"status": target_check["decision"], "message": target_check["reason"], "log": log}

        result = update_presentation(source, target)
        log.append({"stage": "presentation_handler", "result": result})
        if not result["replacements"]:
            return {
                "status": "clarify",
                "message": (
                    "Presentation saved but no {{placeholders}} were replaced. "
                    "Add placeholders like {{revenue}} or {{period}} to slides, then retry."
                ),
                "output_file": result["output_path"],
                "log": log,
            }
        preview = build_presentation_preview(result)
        return {"status": "done", "preview": preview, "output_file": result["output_path"], "log": log}

    if task == "organise_files":
        rule_gate = gate_organise_instruction(prompt)
        log.append({"stage": "confidence_gate_organise", "result": rule_gate})
        if rule_gate["decision"] != "go":
            return {"status": rule_gate["decision"], "message": rule_gate["reason"], "log": log}

        files = [_resolve(f, working_dir) for f in intent["files"]]
        dest = os.path.join(working_dir, "organised")
        result = organise_files(files, prompt, dest)
        log.append({"stage": "file_organizer", "result": result})
        preview = build_organise_preview(result)
        return {"status": "done", "preview": preview, "output_file": dest, "log": log}

    if task == "compare_and_summarize":
        sources = [_resolve(f, working_dir) for f in intent["sources"]]
        gate = gate_comparison_sources(sources)
        log.append({"stage": "confidence_gate_compare", "result": gate})
        if gate["decision"] != "go":
            return {"status": gate["decision"], "message": gate["reason"], "log": log}

        out_dir = os.path.join(working_dir, "output")
        result = compare_and_summarize(sources, out_dir)
        log.append({"stage": "comparison_handler", "result": result})
        preview = build_comparison_preview(result)
        return {"status": "done", "preview": preview, "output_file": result["output_path"], "log": log}

    if task == "correct_document":
        target = _resolve(intent["target_document"], working_dir)
        target_check = check_target_file(target, (".docx",))
        log.append({"stage": "confidence_gate_target", "result": target_check})
        if target_check["decision"] != "go":
            return {"status": target_check["decision"], "message": target_check["reason"], "log": log}

        from handlers.document_corrector import detect_corrections

        doc_text = extract_text(target)["text"]
        corrections = detect_corrections(doc_text, replacements)
        corr_gate = gate_document_corrections(corrections)
        log.append({"stage": "confidence_gate_corrections", "result": corr_gate})
        if corr_gate["decision"] != "go":
            return {"status": corr_gate["decision"], "message": corr_gate["reason"], "log": log}

        result = correct_document(target, replacements)
        log.append({"stage": "document_corrector", "result": result})
        preview = build_correction_preview(result)
        return {"status": "done", "preview": preview, "output_file": result["output_path"], "log": log}

    return {
        "status": "clarify",
        "message": intent.get("reason") or f"Unsupported task: {task}",
        "log": log,
    }
