"""Spins up a throwaway, offscreen desktop (Xvfb + its own D-Bus session +
its own AT-SPI bus) for these tests to drive, so they never touch whatever
real desktop session pytest happens to be running under.
"""
import os
import re
import shutil
import signal
import subprocess
import time

import pytest

_ATSPI_BUS_LAUNCHER = "/usr/libexec/at-spi-bus-launcher"


@pytest.fixture(scope="session", autouse=True)
def isolated_desktop():
    if shutil.which("Xvfb") is None or not os.path.exists(_ATSPI_BUS_LAUNCHER):
        pytest.skip("Xvfb and/or at-spi-bus-launcher not available in this environment")

    display = ":97"
    xvfb = subprocess.Popen(
        ["Xvfb", display, "-screen", "0", "1280x1024x24"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    dbus_launch = subprocess.run(
        ["dbus-launch", "--sh-syntax"], capture_output=True, text=True, check=True,
    )
    bus_address = re.search(r"DBUS_SESSION_BUS_ADDRESS='([^']+)'", dbus_launch.stdout).group(1)
    bus_pid = int(re.search(r"DBUS_SESSION_BUS_PID=(\d+)", dbus_launch.stdout).group(1))

    env = dict(os.environ, DISPLAY=display, DBUS_SESSION_BUS_ADDRESS=bus_address)
    atspi_launcher = subprocess.Popen(
        [_ATSPI_BUS_LAUNCHER], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    # Set for the rest of this test session — the adapter under test and the
    # fixture app it launches both need to see this isolated display/bus.
    os.environ["DISPLAY"] = display
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = bus_address

    yield

    atspi_launcher.terminate()
    try:
        atspi_launcher.wait(timeout=5)
    except subprocess.TimeoutExpired:
        atspi_launcher.kill()
    try:
        os.kill(bus_pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    xvfb.terminate()
    try:
        xvfb.wait(timeout=5)
    except subprocess.TimeoutExpired:
        xvfb.kill()


@pytest.fixture
def accessible_app():
    """Launches the fixture GTK app and waits until it's visible over AT-SPI."""
    import gi

    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi

    app_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "accessible_test_app.py")
    proc = subprocess.Popen(
        ["python3", app_path, "kpi_value_entry", "initial value"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    Atspi.init()
    desktop = Atspi.get_desktop(0)
    deadline = time.monotonic() + 10
    found = False
    while time.monotonic() < deadline:
        for i in range(desktop.get_child_count()):
            if "accessible_test_app" in desktop.get_child_at_index(i).get_name():
                found = True
                break
        if found:
            break
        time.sleep(0.2)
    if not found:
        proc.terminate()
        raise RuntimeError("fixture GTK app never registered with AT-SPI")

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
