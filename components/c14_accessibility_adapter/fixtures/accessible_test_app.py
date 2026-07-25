"""Fixture app for the accessibility adapter's tests.

A minimal GTK window with:
- one named, normal-sized editable entry (role "text")
- one read-only label (role "label")
- one *unnamed*, tiny (1x1) decoy entry, also role "text"

The decoy mirrors what real apps like gedit/LibreOffice do — their main
document editor has no accessible name, and can share a role with other,
irrelevant same-role elements (e.g. a hidden/degenerate-sized one). It lets
tests verify the adapter's "search by role, prefer the largest on-screen
match" disambiguation against something other than production apps that may
not be installed everywhere.

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

decoy = Gtk.Entry()
decoy.set_text("decoy")
decoy.set_size_request(1, 1)
box.add(decoy)

win.add(box)
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
