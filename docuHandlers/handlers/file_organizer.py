"""Organise files according to spoken/written instructions."""
import os
import re
import shutil
from datetime import datetime
from docuHandlers.logger import log_handler


EXT_FOLDERS = {
    ".pdf": "PDFs",
    ".xlsx": "Spreadsheets",
    ".csv": "Spreadsheets",
    ".docx": "Documents",
    ".pptx": "Presentations",
    ".txt": "Text",
    ".md": "Text",
}


def _rule_from_prompt(prompt: str) -> str:
    p = prompt.lower()
    if re.search(r"\b(type|extension|format)\b", p):
        return "by_type"
    if re.search(r"\bdate\b", p):
        return "by_date"
    return "by_type"


@log_handler("file_organizer")
def organise_files(files: list[str], prompt: str, dest_root: str) -> dict:
    rule = _rule_from_prompt(prompt)
    os.makedirs(dest_root, exist_ok=True)
    moves = []

    for src in files:
        if not os.path.exists(src):
            moves.append({"source": src, "status": "skipped", "reason": "not found"})
            continue

        ext = os.path.splitext(src)[1].lower()
        if rule == "by_type":
            folder = EXT_FOLDERS.get(ext, "Other")
        elif rule == "by_date":
            mtime = os.path.getmtime(src)
            folder = datetime.fromtimestamp(mtime).strftime("%Y-%m")
        else:
            folder = "Other"

        target_dir = os.path.join(dest_root, folder)
        os.makedirs(target_dir, exist_ok=True)
        dest = os.path.join(target_dir, os.path.basename(src))

        if os.path.abspath(src) == os.path.abspath(dest):
            moves.append({"source": src, "destination": dest, "status": "unchanged"})
            continue

        shutil.copy2(src, dest)
        moves.append({"source": src, "destination": dest, "status": "copied", "rule": rule})

    return {"dest_root": dest_root, "rule": rule, "moves": moves}
