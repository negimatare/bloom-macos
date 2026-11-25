"""Shared state for the GUI: the saved config, keyboard connection and actions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QObject, QTimer, Signal

from .. import config, device, keymap, layout, lighting, watcher
from ..apply import apply_lighting, apply_mappings, apply_profile
from ..config import Config, Profile
from ..lighting import LightEffect

POLL_MS = 2000


@dataclass
class _Undo:
    name: str
    before: Profile
    only_mappings: bool
    reactivate: bool = False


class Controller(QObject):
    connection_changed = Signal(bool)
    config_changed = Signal()
    message = Signal(str)
    error = Signal(str)
    permission_needed = Signal()  # macOS blocks the keyboard: Input Monitoring is off

    def __init__(self) -> None:
        super().__init__()
        self.config: Config = config.load()
        self._paths: frozenset[bytes] = frozenset()
        self._control_path: bytes | None = None
        self._listening = False
        self._undo: _Undo | None = None
        self._last_assignment: tuple[str, str] | None = None
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.stop_listening)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(POLL_MS)
        self._poll()

    # ---- connection ---------------------------------------------------------

    @property
    def connected(self) -> bool:
        return bool(self._paths)

    @staticmethod
    def lighting_blocked() -> bool:
        """True when macOS denies Input Monitoring, so lighting commands cannot reach the keyboard."""
        return device.input_monitoring_status() == "denied"

    def _poll(self) -> None:
        paths = frozenset(i.path for i in device.list_interfaces())
        if paths == self._paths:
            return
        was_connected = self.connected
        self._paths = paths
        self._control_path = None
        if paths and not self._listening and not self.helper_running():
            # No background helper, so re-apply mappings ourselves.
            self._run(lambda: apply_mappings(self.profile), "")
        if paths:
            # The keyboard misses lighting changes made while it was unplugged.
            self._run(lambda: apply_lighting(self.profile), "")
        if self.connected != was_connected:
            self.connection_changed.emit(self.connected)

    def _keyboard(self) -> device.Keyboard:
        if self._control_path is None:
            self._control_path = device.find_control_interface().path
        return device.Keyboard(self._control_path)

    def _run(self, action, success: str) -> bool:
        try:
            action()
        except (device.DeviceError, keymap.KeymapError, KeyError, ValueError, RuntimeError, OSError) as exc:
            self._control_path = None  # re-probe next time
            if isinstance(exc, device.DeviceError) and self.lighting_blocked():
                self.permission_needed.emit()
            else:
                self.error.emit(str(exc))
            return False
        if success:
            self.message.emit(success)
        return True

    # ---- config -------------------------------------------------------------

    @property
    def profile(self) -> Profile:
        return self.config.active

    def save(self) -> bool:
        try:
            config.save(self.config)
        except OSError as exc:
            self.error.emit(f"The settings can't be saved: {exc}")
            return False
        finally:
            self.config_changed.emit()
        return True

    def _apply_and_save(self, apply: Callable[[], bool]) -> bool:
        """Apply even when the save will fail; a save error comes last, so it stays on screen."""
        applied = apply()
        return self.save() and applied

    # ---- lighting -----------------------------------------------------------

    def _with_keyboard(self, fn) -> None:
        with self._keyboard() as kb:
            fn(kb)

    def set_effect(self, effect: LightEffect) -> None:
        self.profile.lighting.effect = effect.value
        self.save()
        if not self.connected:
            return

        def action(kb):
            lighting.set_effect(kb, effect)
            if effect is not LightEffect.OFF:
                lighting.set_brightness(kb, self.profile.lighting.brightness)

        self._run(lambda: self._with_keyboard(action), "")

    def set_brightness(self, percent: int) -> None:
        self.profile.lighting.brightness = percent
        self.save()
        if self.connected and self.profile.lighting.effect != LightEffect.OFF.value:
            self._run(
                lambda: self._with_keyboard(lambda kb: lighting.set_brightness(kb, percent)), ""
            )

    # ---- key mappings -------------------------------------------------------

    @property
    def listening(self) -> bool:
        return self._listening

    def start_listening(self) -> None:
        """Remove the mappings for a moment, so a key press reports the physical key."""
        if not self._listening:
            self._listening = True
            if self.connected:
                self._run(keymap.clear, "")

    def stop_listening(self) -> None:
        if self._listening:
            self._listening = False
            self._apply_mappings()

    def _apply_mappings(self) -> bool:
        return not self.connected or self._run(lambda: apply_mappings(self.profile), "")

    def _apply_profile(self, success: str = "") -> bool:
        return not self.connected or self._run(lambda: apply_profile(self.profile), success)

    def _keep_undo(self) -> None:
        name = self.config.active_profile
        self._undo = _Undo(name, self.config.profiles[name].copy(), only_mappings=True)
        self._last_assignment = None

    def _set_mappings(self, mappings: list[keymap.Mapping]) -> bool:
        self._listening = False  # the new mappings replace the paused ones
        self.profile.mappings = mappings
        return self._apply_and_save(self._apply_mappings)

    def assign(self, key: str, function: str) -> keymap.Change | None:
        """Make `key` give `function`, by swap when another key gives it now. None if it failed."""
        change = keymap.assign(self.profile.mappings, key, function, layout.KEY_NAMES)
        self._keep_undo()
        self._last_assignment = (key, function)
        return change if self._set_mappings(change.mappings) else None

    def revert(self, key: str) -> keymap.Change | None:
        change = keymap.assign(self.profile.mappings, key, key, layout.KEY_NAMES)
        self._keep_undo()
        return change if self._set_mappings(change.mappings) else None

    def reset_mappings(self) -> bool:
        self._keep_undo()
        return self._set_mappings([])

    def keep_both(self) -> bool:
        """After a swap, give the swapped key its function back too."""
        entry, assignment = self._undo, self._last_assignment
        if entry is None or assignment is None or entry.name != self.config.active_profile:
            return False
        key, function = assignment
        return self._set_mappings(keymap.remap(entry.before.mappings, key, function))

    def undo(self) -> bool:
        """Undo of a remap change keeps the lighting changes made after it."""
        entry = self._undo
        if entry is None:
            return False
        self._undo = self._last_assignment = None
        if entry.only_mappings:
            self.config.profiles[entry.name].mappings = entry.before.mappings
        else:
            self.config.profiles[entry.name] = entry.before
        if entry.reactivate:
            return self.activate(entry.name)
        if entry.name != self.config.active_profile:
            return self.save()
        return self._apply_and_save(self._apply_mappings if entry.only_mappings else self._apply_profile)

    # ---- background helper --------------------------------------------------

    @staticmethod
    def helper_running() -> bool:
        return watcher.agent_status().endswith("running")

    @staticmethod
    def helper_installed() -> bool:
        return watcher.PLIST_PATH.exists()

    def set_helper(self, enabled: bool) -> None:
        if enabled:
            self._run(watcher.agent_install, "Background helper started")
        else:
            self._run(watcher.agent_uninstall, "Background helper removed")

    # ---- profiles -----------------------------------------------------------

    def activate(self, name: str) -> bool:
        self.config.active_profile = name
        if not self.connected:
            self.message.emit(f"Profile '{name}' active. The keyboard isn't connected.")
        return self._apply_and_save(lambda: self._apply_profile(f"Profile '{name}' applied"))

    def _profile_rule(self, rule) -> object | None:
        """Run a `Config` rule; report a refused one and return None."""
        try:
            return rule()
        except config.ProfileError as exc:
            self.error.emit(str(exc))
            return None

    def new_profile(self, name: str, icon: str, copy_of: str | None = None) -> str | None:
        name = self._profile_rule(lambda: self.config.create(name, copy_of))
        if name is not None:
            self.config.profiles[name].icon = icon
            self.save()
        return name

    def edit_profile(self, old: str, new: str, icon: str) -> str | None:
        name = self._profile_rule(lambda: self.config.rename(old, new))
        if name is not None:
            self.config.profiles[name].icon = icon
            self.save()
        return name

    def delete_profile(self, name: str) -> bool:
        was_active = name == self.config.active_profile
        before = self.config.profiles[name].copy()
        try:
            self.config.delete(name)
        except config.ProfileError as exc:
            self.error.emit(str(exc))
            return False
        self._undo = _Undo(name, before, only_mappings=False, reactivate=was_active)
        self._last_assignment = None
        if was_active:
            return self.activate(self.config.active_profile)
        return self.save()

    def restore_default(self, name: str) -> bool:
        self._undo = _Undo(name, self.config.profiles[name].copy(), only_mappings=False)
        self._last_assignment = None
        self.config.restore_default(name)
        if name != self.config.active_profile:
            return self.save()
        return self._apply_and_save(self._apply_profile)

    def export_profile(self, name: str, path: str) -> bool:
        return self._run(lambda: Path(path).write_text(self.config.export_profile(name)), "")

    def import_profile(self, path: str) -> str | None:
        try:
            text = Path(path).read_text()
        except (OSError, UnicodeDecodeError) as exc:
            self.error.emit(f"This file can't be read: {exc}")
            return None
        name = self._profile_rule(lambda: self.config.import_profile(text))
        if name is not None:
            self.save()
        return name
