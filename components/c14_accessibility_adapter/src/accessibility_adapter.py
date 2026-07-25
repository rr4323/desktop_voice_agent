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

try:
    import gi
    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi, GLib
    HAS_GI = True
    GLibError = GLib.Error
except (ImportError, ValueError):
    HAS_GI = False
    Atspi = None
    GLib = None
    GLibError = Exception

_initialized = False


def _ensure_init() -> None:
    global _initialized
    if not HAS_GI:
        raise RuntimeError("AT-SPI / PyGObject (gi) is not installed on this system")
    if not _initialized:
        Atspi.init()
        _initialized = True


def _matches(node, name: str | None, role: str | None) -> bool:
    try:
        name_ok = name is None or node.get_name() == name
    except GLibError:
        name_ok = False
    try:
        role_ok = role is None or node.get_role_name() == role
    except GLibError:
        role_ok = False
    return name_ok and role_ok


def _visible_area(node) -> int:
    try:
        if "Component" not in node.get_interfaces():
            return -1
        extents = Atspi.Component.get_extents(node, Atspi.CoordType.SCREEN)
    except GLibError:
        return -1
    if extents.width <= 0 or extents.height <= 0:
        return -1
    return extents.width * extents.height


def _collect_matches(node, name: str | None, role: str | None, depth: int = 0, max_depth: int = 40) -> list:
    matches = [node] if _matches(node, name, role) else []
    if depth >= max_depth:
        return matches
    for i in range(node.get_child_count()):
        try:
            child = node.get_child_at_index(i)
        except GLibError:
            continue
        matches.extend(_collect_matches(child, name, role, depth + 1, max_depth))
    return matches


def _find_element(app, name: str | None, role: str | None):
    matches = _collect_matches(app, name, role)
    if not matches:
        return None
    # Many real apps (LibreOffice, gedit, ...) expose their main document
    # editing surface with no accessible name at all, sometimes alongside
    # other same-role elements that are hidden/off-screen (e.g. an
    # unrealized popup entry sitting at degenerate coordinates). When more
    # than one node matches, prefer the largest on-screen one — the same
    # heuristic a person would use to pick out "the big text area."
    return max(matches, key=_visible_area)


def _find_app(app_name: str):
    _ensure_init()
    desktop = Atspi.get_desktop(0)
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        try:
            name = app.get_name()
        except GLibError:
            continue
        if name == app_name or app_name.lower() in name.lower():
            return app
    return None


def read_or_write(request: dict[str, Any]) -> dict[str, Any]:
    """Read or write an accessible element in a running app, found by name
    and/or role (at least one of the two is required).

    request (read):  {"operation": "read", "app_name": "...", "element_name"?: "...", "role"?: "..."}
    request (write): {"operation": "write", "app_name": "...", "element_name"?: "...", "role"?: "...", "value": "..."}

    `element_name` alone is enough for widgets with a real accessible name
    (e.g. a labeled entry). `role` (e.g. "text") is for elements that don't
    have one — common for a document editor's main text area — and, when it
    matches more than one element, resolves to the largest on-screen match.
    """
    operation = request["operation"]
    app_name = request["app_name"]
    element_name = request.get("element_name")
    role = request.get("role")
    if element_name is None and role is None:
        raise ValueError("request must include element_name and/or role")

    app = _find_app(app_name)
    if app is None:
        raise LookupError(f"no running app found matching {app_name!r} in the accessibility tree")

    element = _find_element(app, element_name, role)
    if element is None:
        raise LookupError(
            f"no accessible element matching name={element_name!r} role={role!r} found in app {app_name!r}"
        )

    element_role = element.get_role_name()
    label = element_name if element_name is not None else role

    if operation == "read":
        value = Atspi.Text.get_text(element, 0, -1)
        return {
            "value": value,
            "provenance": {"app": app_name, "element": label, "role": element_role},
            "extraction_method": "accessibility_tree",
        }

    if operation == "write":
        value = request["value"]
        if "EditableText" not in element.get_interfaces():
            raise ValueError(
                f"element {label!r} (role={element_role}) is not editable via the accessibility tree"
            )
        previous_value = Atspi.Text.get_text(element, 0, -1)
        Atspi.EditableText.delete_text(element, 0, -1)
        Atspi.EditableText.insert_text(element, 0, value, len(value))
        new_value = Atspi.Text.get_text(element, 0, -1)
        return {
            "success": True,
            "element": label,
            "previous_value": previous_value,
            "new_value": new_value,
        }

    raise ValueError(f"unknown operation: {operation!r}")


if __name__ == "__main__":
    # Manual smoke test:
    #   python -m components.c14_accessibility_adapter.src.accessibility_adapter <app_name> --name <element_name> [value]
    #   python -m components.c14_accessibility_adapter.src.accessibility_adapter <app_name> --role <role> [value]
    import json
    import sys

    app_name_arg = sys.argv[1]
    selector_kind = sys.argv[2]  # "--name" or "--role"
    selector_value = sys.argv[3]
    rest = sys.argv[4:]

    req: dict[str, Any] = {"app_name": app_name_arg}
    req["element_name" if selector_kind == "--name" else "role"] = selector_value

    if rest:
        req["operation"] = "write"
        req["value"] = rest[0]
    else:
        req["operation"] = "read"

    print(json.dumps(read_or_write(req), indent=2))
