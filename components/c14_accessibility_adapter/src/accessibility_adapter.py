"""Accessibility Adapter (component 14): read/write live desktop UI elements
via AT-SPI.

Responsibility: for content the format-native adapters (06-08) can't
resolve — e.g. an embedded chart image, or visually confirming a value in a
running app window — read/write it via the OS accessibility tree instead.
This is TDD §6.4's "accessibility fallback" turned into its own component.

This is deliberately a *secondary* path, not the primary execution route:
reading straight out of a PDF/XLSX/PPTX file is faster and more
deterministic than driving a live GUI (no window to find, no race with the
app's UI thread), so use components 06-08 whenever there's a structured
file to read/write directly, and reach for this adapter only when there
isn't one.
"""
from typing import Any

import gi

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi, GLib  # noqa: E402

_initialized = False


def _ensure_init() -> None:
    global _initialized
    if not _initialized:
        Atspi.init()
        _initialized = True


def _find_by_name(node, name: str):
    try:
        if node.get_name() == name:
            return node
    except GLib.Error:
        pass
    for i in range(node.get_child_count()):
        try:
            child = node.get_child_at_index(i)
        except GLib.Error:
            continue
        found = _find_by_name(child, name)
        if found is not None:
            return found
    return None


def _find_app(app_name: str):
    _ensure_init()
    desktop = Atspi.get_desktop(0)
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        try:
            name = app.get_name()
        except GLib.Error:
            continue
        if name == app_name or app_name.lower() in name.lower():
            return app
    return None


def read_or_write(request: dict[str, Any]) -> dict[str, Any]:
    """Read or write a named accessible element in a running app.

    request (read):  {"operation": "read", "app_name": "...", "element_name": "..."}
    request (write): {"operation": "write", "app_name": "...", "element_name": "...", "value": "..."}
    """
    operation = request["operation"]
    app_name = request["app_name"]
    element_name = request["element_name"]

    app = _find_app(app_name)
    if app is None:
        raise LookupError(f"no running app found matching {app_name!r} in the accessibility tree")

    element = _find_by_name(app, element_name)
    if element is None:
        raise LookupError(f"no accessible element named {element_name!r} found in app {app_name!r}")

    role = element.get_role_name()

    if operation == "read":
        value = Atspi.Text.get_text(element, 0, -1)
        return {
            "value": value,
            "provenance": {"app": app_name, "element": element_name, "role": role},
            "extraction_method": "accessibility_tree",
        }

    if operation == "write":
        value = request["value"]
        if "EditableText" not in element.get_interfaces():
            raise ValueError(
                f"element {element_name!r} (role={role}) is not editable via the accessibility tree"
            )
        previous_value = Atspi.Text.get_text(element, 0, -1)
        Atspi.EditableText.delete_text(element, 0, -1)
        Atspi.EditableText.insert_text(element, 0, value, len(value))
        new_value = Atspi.Text.get_text(element, 0, -1)
        return {
            "success": True,
            "element": element_name,
            "previous_value": previous_value,
            "new_value": new_value,
        }

    raise ValueError(f"unknown operation: {operation!r}")


if __name__ == "__main__":
    # Manual smoke test: python -m components.c14_accessibility_adapter.src.accessibility_adapter <app_name> <element_name> [value_to_write]
    import json
    import sys

    app_name_arg = sys.argv[1]
    element_name_arg = sys.argv[2]
    if len(sys.argv) > 3:
        print(json.dumps(read_or_write({
            "operation": "write", "app_name": app_name_arg,
            "element_name": element_name_arg, "value": sys.argv[3],
        }), indent=2))
    else:
        print(json.dumps(read_or_write({
            "operation": "read", "app_name": app_name_arg, "element_name": element_name_arg,
        }), indent=2))
