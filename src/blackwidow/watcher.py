"""Background helper: re-apply key mappings whenever the keyboard (re)connects.

macOS forgets hidutil mappings when the keyboard is unplugged, on reboot, and
possibly after sleep. The keyboard keeps its own lighting, so only mappings
need re-applying. This only enumerates USB devices and calls hidutil; it never
opens the keyboard, so it needs no Input Monitoring permission.
"""

from __future__ import annotations

import logging
import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path

import hid

from . import config, keymap
from .device import PRODUCT_ID, VENDOR_ID

log = logging.getLogger("blackwidow.watch")

POLL_SECONDS = 2.0
SETTLE_SECONDS = 1.0  # let macOS finish setting up the services after attach

LABEL = "com.blackwidowcontrol.watch"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOG_PATH = Path.home() / "Library" / "Logs" / "BlackWidowControl" / "watch.log"


def _connected_paths() -> frozenset[bytes]:
    return frozenset(d["path"] for d in hid.enumerate(VENDOR_ID, PRODUCT_ID))


def _config_mtime() -> float:
    try:
        return config.CONFIG_PATH.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def apply_mappings() -> None:
    mappings = config.load().active.mappings
    keymap.apply(mappings)
    log.info("applied %d mapping(s)", len(mappings))


def watch() -> None:
    """Run forever. Applies on start, on every (re)connect and on config change."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout
    )
    log.info("watching for Razer BlackWidow Lite (%04x:%04x)", VENDOR_ID, PRODUCT_ID)
    last_paths: frozenset[bytes] = frozenset()
    last_mtime = -1.0
    while True:
        try:
            paths = _connected_paths()
            mtime = _config_mtime()
            reconnected = paths and paths != last_paths
            if reconnected:
                log.info("keyboard connected")
                time.sleep(SETTLE_SECONDS)
            elif not paths and last_paths:
                log.info("keyboard disconnected")
            if paths and (reconnected or mtime != last_mtime):
                apply_mappings()
            last_paths, last_mtime = paths, mtime
        except Exception:  # keep the helper alive whatever happens
            log.exception("error; retrying")
        time.sleep(POLL_SECONDS)


# ---- LaunchAgent (start at login) -------------------------------------------


def _bw_executable() -> str:
    """The `bw` script in this project's virtualenv."""
    exe = Path(sys.executable).with_name("bw")
    if not exe.exists():
        raise RuntimeError(f"cannot find bw executable next to {sys.executable}")
    return str(exe)


def _launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["/bin/launchctl", *args], capture_output=True, text=True)


def _domain() -> str:
    return f"gui/{os.getuid()}"


def agent_install() -> Path:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": LABEL,
        "ProgramArguments": [_bw_executable(), "watch"],
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Background",
        "StandardOutPath": str(LOG_PATH),
        "StandardErrorPath": str(LOG_PATH),
    }
    agent_uninstall()  # replace any previous version
    PLIST_PATH.write_bytes(plistlib.dumps(plist))
    result = _launchctl("bootstrap", _domain(), str(PLIST_PATH))
    if result.returncode != 0:
        raise RuntimeError(f"launchctl bootstrap failed: {result.stderr.strip()}")
    return PLIST_PATH


def agent_uninstall() -> bool:
    """Stop the helper and remove it from login. True if it was installed."""
    _launchctl("bootout", f"{_domain()}/{LABEL}")
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
        return True
    return False


def agent_status() -> str:
    if not PLIST_PATH.exists():
        return "not installed"
    result = _launchctl("print", f"{_domain()}/{LABEL}")
    if result.returncode != 0:
        return "installed, not running"
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("state ="):
            return f"installed, {line.split('=', 1)[1].strip()}"
    return "installed"
