"""Minimal macOS app bundles around a `bloom` command, so macOS shows Bloom's name and icon."""

from __future__ import annotations

import plistlib
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from . import APP_NAME, ICON_ICNS

LSREGISTER = ("/System/Library/Frameworks/CoreServices.framework/Frameworks/"
              "LaunchServices.framework/Support/lsregister")


def venv_script(name: str) -> str:
    """A script of this project's virtualenv, such as `bloom` or `bloom-gui`."""
    exe = Path(sys.executable).with_name(name)
    if not exe.exists():
        raise RuntimeError(f"cannot find {name} executable next to {sys.executable}")
    return str(exe)


def write_app_bundle(bundle: Path, bundle_id: str, command: str, *, background: bool) -> Path:
    """Write `bundle`; its executable runs `command`. Return the executable."""
    contents = bundle / "Contents"
    (contents / "MacOS").mkdir(parents=True, exist_ok=True)
    (contents / "Resources").mkdir(parents=True, exist_ok=True)
    info = {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": bundle_id,
        # macOS lists a login item under its executable name
        "CFBundleExecutable": APP_NAME,
        "CFBundleIconFile": ICON_ICNS.stem,
        "CFBundlePackageType": "APPL",
        "NSHighResolutionCapable": True,
    }
    if background:
        info["LSBackgroundOnly"] = True
    (contents / "Info.plist").write_bytes(plistlib.dumps(info))
    shutil.copyfile(ICON_ICNS, contents / "Resources" / ICON_ICNS.name)
    executable = contents / "MacOS" / APP_NAME
    executable.write_text(f"#!/bin/sh\nexec {command}\n")
    executable.chmod(0o755)
    return executable


def quoted(*args: str) -> str:
    return " ".join(shlex.quote(a) for a in args)


def register(bundle: Path) -> None:
    """Tell Launch Services about `bundle`, so Finder and Launchpad show its name and icon."""
    subprocess.run([LSREGISTER, "-f", str(bundle)], capture_output=True)


def unregister(bundle: Path) -> None:
    subprocess.run([LSREGISTER, "-u", str(bundle)], capture_output=True)
