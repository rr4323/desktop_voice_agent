"""Tool wrapper around docuHandlers/handlers/file_organizer.py."""
from typing import Any

from docuHandlers.handlers.file_organizer import organise_files


class OrganizeFilesTool:
    app_name = "organize_files"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]
        result = organise_files(target["files"], target.get("prompt", ""), target["dest_root"])
        return {"success": True, **result}
