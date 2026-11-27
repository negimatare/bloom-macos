import os
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "drive.py"

# Loaded before the driver through PYTHONPATH: it breaks LightingStudio once
# bloom.gui.lighting_studio loads, without importing bloom itself.
_BREAK_LIGHTING = """
import importlib.abc, importlib.util, sys

class Break(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name != "bloom.gui.lighting_studio":
            return None
        sys.meta_path.remove(self)
        spec = importlib.util.find_spec(name)
        load = spec.loader.exec_module
        def exec_module(module):
            load(module)
            def broken(*args, **kwargs):
                raise RuntimeError("planted")
            module.LightingStudio.__init__ = broken
        spec.loader.exec_module = exec_module
        return spec

sys.meta_path.insert(0, Break())
"""


def drive(out: Path, *args: str, hook: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    extra = dict(env or {})
    if hook is not None:
        folder = out.parent / "hook"
        folder.mkdir(exist_ok=True)
        (folder / "sitecustomize.py").write_text(hook)
        extra["PYTHONPATH"] = str(folder)
    return subprocess.run([sys.executable, str(_SCRIPT), "--out", str(out), *args],
                          capture_output=True, text=True, timeout=120, env={**os.environ, **extra})


def test_the_driver_saves_each_screen_on_the_sample_and_fakes(tmp_path):
    result = drive(tmp_path / "out")
    assert result.returncode == 0, result.stdout + result.stderr
    out = tmp_path / "out"
    for screen in ("Lighting", "Keymap", "Profiles"):
        assert (out / f"{screen}.png").exists()
    log = (out / "log.txt").read_text()
    # Only the sample config has these: the window read it.
    assert "keyboard: mappings [('caps_lock', 'left_control')]" in log
    assert "keyboard: lighting static 80%" in log
    for real in ("hidutil:", "launchctl:", "helper install:", "error", "exception"):
        assert real not in log


def test_one_screen(tmp_path):
    result = drive(tmp_path / "out", "--screen", "Profiles")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "out" / "Profiles.png").exists()
    assert not (tmp_path / "out" / "Lighting.png").exists()


def test_an_exception_in_the_window_fails_the_run_and_is_printed(tmp_path):
    result = drive(tmp_path / "out", hook=_BREAK_LIGHTING)
    assert result.returncode == 1
    assert "RuntimeError: planted" in (tmp_path / "out" / "log.txt").read_text()
    assert "RuntimeError: planted" in result.stderr


def test_a_config_read_before_the_driver_fails_the_run(tmp_path):
    other = tmp_path / "other.json"
    result = drive(tmp_path / "out", hook="import bloom.config\n", env={"BLOOM_CONFIG": str(other)})
    assert result.returncode == 1
    assert "not the sample" in result.stderr
    assert not (tmp_path / "out" / "Lighting.png").exists()


def test_an_unknown_screen_is_refused(tmp_path):
    result = drive(tmp_path / "out", "--screen", "Settings")
    assert result.returncode == 2
    assert "invalid choice: 'Settings'" in result.stderr
