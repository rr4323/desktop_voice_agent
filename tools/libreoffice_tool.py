"""Tool wrapper around components/c16_libreoffice_adapter: headless
document format conversion for formats the native adapters don't handle.
"""
from typing import Any

from components.c16_libreoffice_adapter.src.libreoffice_adapter import convert


class LibreOfficeTool:
    app_name = "libreoffice"

    def run(self, step: dict[str, Any]) -> dict[str, Any]:
        target = step["target"]
        return convert(
            {
                "file": target["file"],
                "target_format": target["target_format"],
                "filter_name": target.get("filter_name"),
                "output_dir": target.get("output_dir"),
            }
        )
