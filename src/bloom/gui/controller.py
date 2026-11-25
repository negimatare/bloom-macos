"""Shared state for the GUI: the saved config, keyboard connection and actions."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QObject, QTimer, Signal

from .. import config, device, keymap, layout, lighting, watcher
from ..apply import apply_lighting, apply_mappings, apply_profile
from ..config import Config, Profile
from ..lighting import LightEffect

POLL_MS = 2000


class Controller(QObject):
    connection_changed = Signal(bool)
    config_changed = Signal()
    message = Signal(str)
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.config: Config = config.load()
        self._paths: frozenset[bytes] = frozenset()
        self._control_path: bytes | None = None
        self._listening = False
        self._undo: tuple[str, Profile] | None = None
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
        if self.connected != was_connected:
            self.connection_changed.emit(self.connected)

    def _keyboard(self) -> device.Keyboard:
        if self._control_path is None:
            self._control_path = device.find_control_interface().path
        return device.Keyboard(self._control_path)

    def _run(self, action, success: str) -> bool:
        try:
            action()
        except (device.DeviceError, keymap.KeymapError, KeyError, ValueError, RuntimeError) as exc:
            self._control_path = None  # re-probe next time
            self.error.emit(str(exc))
            return False
        if success:
            self.message.emit(success)
        return True

    # ---- config -------------------------------------------------------------

    @property
    def profile(self) -> Profile:
        return self.config.active

    def save(self) -> None:
        config.save(self.config)
        self.config_changed.emit()

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

    def _apply_mappings(self) -> None:
        if self.connected:
            self._run(lambda: apply_mappings(self.profile), "")

    def _keep_undo(self) -> None:
        self._undo = (self.config.active_profile, Profile.from_dict(self.profile.to_dict()))
        self._last_assignment = None

    def _set_mappings(self, mappings: list[keymap.Mapping]) -> None:
        self._listening = False  # the new mappings replace the paused ones
        self.profile.mappings = mappings
        self.save()
        self._apply_mappings()

    def assign(self, key: str, function: str) -> keymap.Change:
        """Make `key` give `function`, by swap when another key gives it now."""
        change = keymap.assign(self.profile.mappings, key, function, layout.KEY_NAMES)
        self._keep_undo()
        self._last_assignment = (key, function)
        self._set_mappings(change.mappings)
        return change

    def revert(self, key: str) -> keymap.Change:
        change = keymap.assign(self.profile.mappings, key, key, layout.KEY_NAMES)
        self._keep_undo()
        self._set_mappings(change.mappings)
        return change

    def reset_mappings(self) -> None:
        self._keep_undo()
        self._set_mappings([])

    def keep_both(self) -> None:
        """After a swap, give the swapped key its function back too."""
        if self._undo is None or self._last_assignment is None:
            return
        name, before = self._undo
        if name != self.config.active_profile:
            return
        key, function = self._last_assignment
        self._set_mappings(keymap.remap(before.mappings, key, function))

    def undo(self) -> None:
        if self._undo is None:
            return
        name, before = self._undo
        self._undo = self._last_assignment = None
        if name not in self.config.profiles:
            return
        self.config.profiles[name] = before
        self.save()
        if name == self.config.active_profile and self.connected:
            self._run(lambda: apply_profile(self.profile), "")

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

    def activate(self, name: str) -> None:
        self.config.active_profile = name
        self.save()
        if not self.connected:
            self.message.emit(f"Profile '{name}' active. The keyboard isn't connected.")
            return

        def action():
            apply_lighting(self.profile)
            apply_mappings(self.profile)

        self._run(action, f"Profile '{name}' applied")

    def _check_name(self, name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("profile name can't be empty")
        if name in self.config.profiles:
            raise ValueError(f"a profile called '{name}' already exists")
        return name

    def new_profile(self, name: str, copy_of: str | None = None) -> bool:
        try:
            name = self._check_name(name)
        except ValueError as exc:
            self.error.emit(str(exc))
            return False
        source = self.config.profiles.get(copy_of) if copy_of else None
        self.config.profiles[name] = (
            Profile.from_dict(source.to_dict()) if source else Profile()
        )
        self.save()
        self.message.emit(f"Profile '{name}' created")
        return True

    def rename_profile(self, old: str, new: str) -> bool:
        try:
            new = self._check_name(new)
        except ValueError as exc:
            self.error.emit(str(exc))
            return False
        # Rebuild to keep the order of profiles.
        self.config.profiles = {
            (new if k == old else k): v for k, v in self.config.profiles.items()
        }
        if self.config.active_profile == old:
            self.config.active_profile = new
        self.save()
        self.message.emit(f"Renamed to '{new}'")
        return True

    def delete_profile(self, name: str) -> bool:
        if len(self.config.profiles) <= 1:
            self.error.emit("You need at least one profile")
            return False
        was_active = name == self.config.active_profile
        del self.config.profiles[name]
        if was_active:
            self.activate(next(iter(self.config.profiles)))
        else:
            self.save()
        self.message.emit(f"Profile '{name}' deleted")
        return True
