"""
Classify user intent from a natural-language prompt and explicitly supplied files.

Supported task types:
  - pdf_to_spreadsheet   Locate PDF info and enter into spreadsheet
  - update_presentation  Update slides using another document
  - organise_files       Organise files per spoken/written instructions
  - compare_and_summarize  Compare docs and produce a summary
  - correct_document       Fix a document while preserving formatting
  - cancel               User cancels an in-flight task
  - change               User revises an in-flight task
"""
import os
import re


TASK_RULES = [
    {
        "task_type": "cancel",
        "patterns": [
            r"\b(cancel|stop|abort|nevermind|never mind|forget it|don't do that)\b",
        ],
        "min_files": 0,
    },
    {
        "task_type": "pdf_to_spreadsheet",
        "patterns": [
            r"locate.*(?:pdf|document).*(?:spreadsheet|excel|xlsx|csv)",
            r"(?:pdf|document).*(?:enter|put|add|merge).*(?:spreadsheet|excel|xlsx|csv)",
            r"(?:extract|pull).*(?:pdf|document).*(?:spreadsheet|excel|sheet)",
        ],
        "min_files": 2,
        "need_exts": {".pdf": 1, ".xlsx": 1, ".csv": 1},  # at least one pdf and one sheet-like
    },
    {
        "task_type": "pdf_to_doc",
        "patterns": [
            r"locate.*(?:pdf|document).*(?:docx|doc|word|document)",
            r"(?:pdf|document).*(?:enter|put|add|merge|insert|transfer|populate).*(?:docx|doc|word|document)",
            r"(?:extract|pull).*(?:pdf|document).*(?:docx|doc|word|document)",
            r"update.*(?:docx|doc|word|document).*(?:using|from|with).*(?:pdf|document|report)",
        ],
        "min_files": 2,
        "need_exts": {".pdf": 1, ".docx": 1},
    },
    {
        "task_type": "update_presentation",
        "patterns": [
            r"update.*presentation",
            r"presentation.*(?:using|from|with).*(?:document|pdf|report|source)",
            r"(?:slide|deck|pptx).*(?:update|refresh|populate)",
        ],
        "min_files": 2,
        "need_exts": {".pptx": 1},
    },
    {
        "task_type": "organise_files",
        "patterns": [
            r"organis[ez].*files",
            r"sort.*files",
            r"group.*files",
            r"arrange.*files",
            r"move.*files.*(?:folder|directory|type)",
        ],
        "min_files": 1,
    },
    {
        "task_type": "compare_and_summarize",
        "patterns": [
            r"compare.*(?:across|between|information|documents|applications|files)",
            r"create.*summary",
            r"summari[sz]e.*(?:difference|comparison|documents|files)",
            r"cross[- ]check",
        ],
        "min_files": 2,
    },
    {
        "task_type": "correct_document",
        "patterns": [
            r"correct.*document",
            r"fix.*(?:spelling|typo|grammar|errors)",
            r"preserv.*format",
            r"edit.*(?:while|without).*(?:format|formatting|layout)",
        ],
        "min_files": 1,
        "need_exts": {".docx": 1},
    },
]


def _exts(files: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        counts[ext] = counts.get(ext, 0) + 1
    return counts


def _has_sheet(ext_counts: dict[str, int]) -> bool:
    return ext_counts.get(".xlsx", 0) + ext_counts.get(".csv", 0) >= 1


def _match_files(task_type: str, files: list[str]) -> dict[str, str]:
    """Pick source/target roles from supplied files."""
    by_ext: dict[str, list[str]] = {}
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        by_ext.setdefault(ext, []).append(f)

    if task_type == "pdf_to_spreadsheet":
        return {
            "source_pdf": by_ext.get(".pdf", [None])[0],
            "target_sheet": (by_ext.get(".xlsx") or by_ext.get(".csv") or [None])[0],
        }
    if task_type == "pdf_to_doc":
        return {
            "source_pdf": by_ext.get(".pdf", [None])[0],
            "target_document": (by_ext.get(".docx") or [None])[0],
        }
    if task_type == "update_presentation":
        source = (by_ext.get(".pdf") or by_ext.get(".docx") or by_ext.get(".txt") or files)[:1]
        return {
            "source_document": source[0] if source else None,
            "target_presentation": (by_ext.get(".pptx") or [None])[0],
        }
    if task_type == "organise_files":
        return {"files": files}
    if task_type == "compare_and_summarize":
        return {"sources": files}
    if task_type == "correct_document":
        return {"target_document": (by_ext.get(".docx") or [None])[0]}
    return {}


def _validate_files(task_type: str, files: list[str]) -> tuple[str, str | None]:
    if not files and task_type not in ("cancel", "change"):
        return "clarify", "No files were provided. Pass files with --files."

    ext_counts = _exts(files)
    rule = next((r for r in TASK_RULES if r["task_type"] == task_type), None)
    if rule is None:
        return "clarify", f"Unknown task type: {task_type}"

    if len(files) < rule.get("min_files", 0):
        return "clarify", f"This task needs at least {rule['min_files']} file(s); got {len(files)}."

    need = rule.get("need_exts")
    if need:
        if task_type == "pdf_to_spreadsheet":
            if ext_counts.get(".pdf", 0) < 1:
                return "clarify", "Need at least one PDF source file."
            if not _has_sheet(ext_counts):
                return "clarify", "Need at least one spreadsheet (.xlsx or .csv)."
        elif task_type == "pdf_to_doc":
            if ext_counts.get(".pdf", 0) < 1:
                return "clarify", "Need at least one PDF source file."
            if ext_counts.get(".docx", 0) < 1:
                return "clarify", "Need at least one Word document (.docx)."
        elif task_type == "update_presentation":
            if ext_counts.get(".pptx", 0) < 1:
                return "clarify", "Need a .pptx presentation to update."
            if len(files) < 2:
                return "clarify", "Need a source document plus the presentation."
        elif task_type == "correct_document":
            if ext_counts.get(".docx", 0) < 1:
                return "clarify", "Document correction requires a .docx file."

    return "go", None


def _score_task(prompt: str) -> list[tuple[str, int]]:
    prompt_l = prompt.lower()
    scores: list[tuple[str, int]] = []
    for rule in TASK_RULES:
        if rule["task_type"] == "cancel":
            continue
        hits = sum(1 for p in rule["patterns"] if re.search(p, prompt_l))
        if hits:
            scores.append((rule["task_type"], hits))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def parse_intent(prompt: str, files: list[str] | None = None) -> dict:
    files = files or []
    prompt_l = prompt.lower()

    # Mid-instruction cancel
    for rule in TASK_RULES:
        if rule["task_type"] != "cancel":
            continue
        if any(re.search(p, prompt_l) for p in rule["patterns"]):
            return {
                "task_type": "cancel",
                "decision": "go",
                "reason": "Cancellation detected in prompt.",
            }

    # Mid-instruction change
    if re.search(r"\b(instead|actually|change to|switch to|rather|on second thought)\b", prompt_l):
        # Re-parse without change keywords influencing cancel
        clean = re.sub(r"\b(instead|actually|change to|switch to|rather|on second thought)\b", "", prompt_l)
        scores = _score_task(clean)
        if scores:
            task_type = scores[0][0]
            decision, reason = _validate_files(task_type, files)
            roles = _match_files(task_type, files)
            return {
                "task_type": "change",
                "new_task_type": task_type,
                "decision": decision,
                "reason": reason or f"Switching to {task_type}.",
                **roles,
            }

    scores = _score_task(prompt)
    if not scores:
        return {
            "task_type": "unknown",
            "decision": "clarify",
            "reason": (
                "Could not determine the task. Supported requests include: "
                "locate PDF info into a spreadsheet or Word document, update a presentation from a document, "
                "organise files, compare documents and summarize, or correct a document."
            ),
        }

    task_type = scores[0][0]
    decision, reason = _validate_files(task_type, files)
    roles = _match_files(task_type, files)
    return {
        "task_type": task_type,
        "decision": decision,
        "reason": reason,
        **roles,
    }

