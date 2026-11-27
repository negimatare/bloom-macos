"""Open the Bloom window with nothing real behind it, and save each screen.

    uv run python scripts/drive.py --out <dir> [--screen Lighting] ...

The keyboard, hidutil, the background helper and macOS settings are fakes,
so no keyboard is needed and nothing reaches USB, the key mappings of the
Mac or ~/Library. The config is a sample in <dir>, never the user's. Writes
<dir>/<screen>.png for each screen (all of them by default) and <dir>/log.txt
with each call that would have left the app, each message and error the
window showed, and any exception. Exits 1 when the log has an error or an
exception, and prints them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace

SCREENS = ("Lighting", "Keymap", "Profiles")
SAMPLE_CONFIG = {
    "active_profile": "Default",
    "profiles": {
        "Default": {
            "icon": "keyboard",
            "lighting": {"effect": "static", "brightness": 80},
            "mappings": [["caps_lock", "left_control"]],
        },
        "Coding": {
            "icon": "code",
            "lighting": {"effect": "breathing", "brightness": 40},
            "mappings": [["left_option", "left_command"], ["left_command", "left_option"]],
        },
    },
}


class Log:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.failed = False

    def add(self, kind: str, text: str) -> None:
        self.lines.append(f"{kind}: {text}")
        if kind in ("error", "exception"):
            self.failed = True


def fake_outside(out: Path, log: Log) -> None:
    """Replace each call that leaves the app with one that only logs it."""
    from bloom import device, keymap, watcher
    from bloom.gui import controller

    keyboard = SimpleNamespace(path=b"fake-blackwidow-lite", describe=lambda: "fake BlackWidow Lite")
    device.list_interfaces = lambda: [keyboard]
    device.find_control_interface = lambda: keyboard
    device.input_monitoring_status = lambda: "granted"

    def no_usb(*_args, **_kwargs):
        raise device.DeviceError("the driver has no keyboard: a call reached the USB layer")

    device.Keyboard = no_usb

    def logged(kind: str, result=None):
        def call(*args, **_kwargs):
            log.add(kind, " ".join(map(str, args)))
            return result
        return call

    # The helper is not installed: no plist in ~/Library, no launchctl.
    watcher.PLIST_PATH = out / "no-helper.plist"
    watcher.agent_status = lambda: "not installed"
    watcher.agent_install = logged("helper install", out / "no-helper.plist")
    watcher.agent_uninstall = logged("helper uninstall", False)
    watcher._launchctl = logged("launchctl", SimpleNamespace(returncode=1, stdout="", stderr=""))
    keymap._hidutil = logged("hidutil", "")
    controller.apply_mappings = lambda p: log.add("keyboard", f"mappings {p.mappings}")
    controller.apply_lighting = lambda p: log.add(
        "keyboard", f"lighting {p.lighting.effect} {p.lighting.brightness}%")
    controller.apply_profile = lambda p: log.add(
        "keyboard", f"profile {p.mappings} {p.lighting.effect} {p.lighting.brightness}%")


def show(names: list[str], out: Path, log: Log) -> None:
    from PySide6.QtWidgets import QApplication

    from bloom.gui import app as bloom_app
    from bloom.gui import theme

    if [name for name, _ in bloom_app.SCREENS] != list(SCREENS):
        raise RuntimeError(f"the window's screens are now {bloom_app.SCREENS}: update SCREENS")
    qt = QApplication.instance() or QApplication([])
    theme.apply(qt)
    window = bloom_app.MainWindow()
    window.c.message.connect(lambda text: log.add("message", text))
    window.c.error.connect(lambda text: log.add("error", text))
    window.c.permission_needed.connect(lambda: log.add("error", "the window asked for Input Monitoring"))
    window.show()
    qt.processEvents()
    for index, name in enumerate(SCREENS):
        if name not in names:
            continue
        window.nav.button(index).setChecked(True)
        window.pages.setCurrentIndex(index)
        qt.processEvents()
        path = out / f"{name}.png"
        if not window.grab().save(str(path)):
            log.add("error", f"could not save {path.name}")
        log.add("screen", f"{name} -> {path.name}")
    window.close()
    qt.processEvents()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="folder for the screenshots and the log")
    parser.add_argument("--screen", action="append", choices=SCREENS,
                        help="a screen to save; all of them by default")
    args = parser.parse_args(argv)

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    config_path = out / "config.json"
    config_path.write_text(json.dumps(SAMPLE_CONFIG, indent=2) + "\n")
    # Before bloom is imported: it reads both when it loads.
    os.environ["BLOOM_CONFIG"] = str(config_path)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    log = Log()
    # An exception in a Qt slot goes to the hook, one anywhere else to the
    # except below; both land in the log.
    sys.excepthook = lambda kind, value, tb: log.add(
        "exception", "".join(traceback.format_exception(kind, value, tb)).strip())
    try:
        from bloom import config

        if config.CONFIG_PATH != config_path:
            # Something imported bloom first, so the window would read that config.
            log.add("error", f"bloom reads {config.CONFIG_PATH}, not the sample: run the driver in its own process")
        else:
            fake_outside(out, log)
            show(args.screen or list(SCREENS), out, log)
    except Exception:
        log.add("exception", traceback.format_exc().strip())
    finally:
        (out / "log.txt").write_text("\n".join(log.lines) + "\n")
    if log.failed:
        print("\n".join(line for line in log.lines if line.startswith(("error", "exception"))), file=sys.stderr)
    print(f"{'Failed' if log.failed else 'Done'}: {out}")
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())
