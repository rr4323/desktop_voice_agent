"""Fixture app for the accessibility adapter's tests.

A minimal GTK window with one editable entry and one read-only label, both
with known accessible names, so tests can drive a real (if throwaway) app
via AT-SPI instead of mocking the accessibility tree.

Usage: python3 accessible_test_app.py [entry_name] [initial_text]
"""
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

entry_name = sys.argv[1] if len(sys.argv) > 1 else "kpi_value_entry"
initial_text = sys.argv[2] if len(sys.argv) > 2 else "initial value"

win = Gtk.Window(title="AccessibilityAdapterTestApp")
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

entry = Gtk.Entry()
entry.set_text(initial_text)
entry.get_accessible().set_name(entry_name)
box.add(entry)

label = Gtk.Label(label="read only label")
label.get_accessible().set_name("readonly_label")
box.add(label)

win.add(box)
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
