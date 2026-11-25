"""The launcher: a small app in ~/Applications that opens the Bloom window."""

from __future__ import annotations

import shutil
from pathlib import Path

from . import APP_NAME, BUNDLE_ID, bundle

APP_BUNDLE = Path.home() / "Applications" / f"{APP_NAME}.app"


def write_launcher_bundle(path: Path, gui_executable: str) -> Path:
    return bundle.write_app_bundle(path, BUNDLE_ID, bundle.quoted(gui_executable), background=False)


def app_install() -> Path:
    gui_executable = bundle.venv_script("bloom-gui")
    app_uninstall()  # replace any previous version
    write_launcher_bundle(APP_BUNDLE, gui_executable)
    bundle.register(APP_BUNDLE)
    return APP_BUNDLE


def app_uninstall() -> bool:
    """Remove the launcher. True if it was installed."""
    if not APP_BUNDLE.exists():
        return False
    bundle.unregister(APP_BUNDLE)
    shutil.rmtree(APP_BUNDLE)
    return True
