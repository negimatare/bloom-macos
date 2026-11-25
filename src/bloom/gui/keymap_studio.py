"""Keymap Studio: click a key, press the key it should become, done."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from .. import keymap, layout
from . import theme
from .controller import Controller
from .keycaps import FN_TOOLTIP, KeyboardGrid, function_text, key_title
from .key_listener import KeyListener
from .key_panel import KeyPanel
from .remaps_list import RemapsList
from .widgets import StatusLine, Toast, ToggleSwitch, card, label, text_block

def _swatch(colour: str, border: str, text: str) -> QHBoxLayout:
    box = QLabel()
    box.setFixedSize(10, 10)
    box.setStyleSheet(f"background: {colour}; border: 1px solid {border}; border-radius: 3px;")
    row = QHBoxLayout()
    row.setSpacing(6)
    row.addWidget(box)
    row.addWidget(label(text, "muted"))
    return row


class KeymapStudio(QWidget):
    def __init__(self, controller: Controller, toast: Toast) -> None:
        super().__init__()
        self.c = controller
        self.toast = toast
        self._selected: str | None = None
        self._capturing = False
        self._listen_profile = ""
        self._unsupported_key = False

        self.badge = label(role="badge")
        header = QHBoxLayout()
        header.addLayout(text_block(
            "Keymap", "Click a key, then press the key it should become.", "title"), 1)
        header.addWidget(self.badge, alignment=Qt.AlignTop)

        self.grid = KeyboardGrid()
        self.grid.key_clicked.connect(self._on_key)
        keyboard = card()
        keyboard_layout = QVBoxLayout(keyboard)
        keyboard_layout.setContentsMargins(12, 12, 12, 12)
        keyboard_layout.addWidget(self.grid)
        legend = QHBoxLayout()
        legend.setSpacing(18)
        legend.addLayout(_swatch(theme.ACCENT, theme.ACCENT, "Selected"))
        legend.addLayout(_swatch(theme.REMAPPED, theme.REMAPPED_BORDER, "Remapped"))
        legend.addLayout(_swatch(theme.KEY, theme.BORDER_STRONG, "Original"))
        legend.addStretch(1)
        keyboard_layout.addLayout(legend)

        self.panel = KeyPanel()
        self.panel.remap_clicked.connect(self._start_listening)
        self.panel.cancel_clicked.connect(lambda: self._finish(None))

        self.remaps = RemapsList()
        self.remaps.revert_clicked.connect(self._revert)
        self.remaps.reset_clicked.connect(self._reset_all)

        self.helper = ToggleSwitch("Keep remaps after reconnecting")
        self.helper.setChecked(self.c.helper_installed())
        self.helper.toggled.connect(self._on_helper)
        helper_row = QHBoxLayout()
        helper_row.addLayout(text_block(
            "Keep remaps after reconnecting",
            "macOS forgets remaps when the keyboard is unplugged or the Mac restarts. "
            "A small helper puts them back, and starts at login."), 1)
        helper_row.addWidget(self.helper)

        self.status = StatusLine()
        footer = QHBoxLayout()
        footer.addWidget(self.status, 1)
        footer.addWidget(label("Razer BlackWidow Lite", "muted"))

        content = QWidget()
        page = QVBoxLayout(content)
        page.setContentsMargins(24, 20, 24, 16)
        page.setSpacing(14)
        page.addLayout(header)
        page.addWidget(keyboard)
        page.addWidget(self.panel)
        page.addWidget(self.remaps)
        page.addLayout(helper_row)
        page.addStretch(1)
        page.addLayout(footer)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.listener = KeyListener()
        self.listener.captured.connect(self._finish)
        self.listener.unsupported.connect(self._on_unsupported_key)
        self.listener.clicked_outside.connect(lambda: self._finish(None))
        QApplication.instance().applicationStateChanged.connect(self._on_app_state)
        self.c.config_changed.connect(self.refresh)
        self.c.connection_changed.connect(self._show_footer)
        self.refresh()

    # ---- listening -----------------------------------------------------------

    def _on_key(self, key: layout.Key) -> None:
        if key.name is None:
            QToolTip.showText(QCursor.pos(), FN_TOOLTIP, self)
            return
        self._selected = key.name
        self._start_listening()

    def _start_listening(self) -> None:
        if self._capturing or self._selected is None:
            return
        self._capturing = True
        self._unsupported_key = False
        self._listen_profile = self.c.config.active_profile
        self.c.start_listening()
        self.listener.start(self.grid.caps[self._selected], self.panel.cancel_button)
        self.refresh()

    def _finish(self, function: str | None) -> None:
        """The one way out of listening: with the captured function, or cancelled."""
        if not self._capturing:
            return
        self._capturing = False
        self.listener.stop()
        current = keymap.function_of(self.c.profile.mappings, self._selected)
        if function is None or function == current:
            self.c.stop_listening()
            if function is not None:
                self.toast.show_message(f"{key_title(self._selected)} already gives {function_text(function)}.")
        else:
            self._assign(self._selected, function)
        self.refresh()

    def _on_unsupported_key(self) -> None:
        self._unsupported_key = True
        self._show_panel()

    def _on_app_state(self, state: Qt.ApplicationState) -> None:
        if state != Qt.ApplicationActive:
            self._finish(None)

    def hideEvent(self, event) -> None:
        self._finish(None)
        super().hideEvent(event)

    # ---- changes and their toasts ----------------------------------------------

    def _tail(self) -> str:
        return "" if self.c.connected else " It applies when the keyboard connects."

    def _assign(self, key: str, function: str) -> None:
        old = keymap.function_of(self.c.profile.mappings, key)
        change = self.c.assign(key, function)
        undo = ("Undo", self._undo)
        self._flash(key, change.swapped_with)
        if change.swapped_with:
            partner = change.swapped_with
            self.toast.show_message(
                f"<b>Swap complete</b><br>{key_title(key)} now gives {function_text(function)}. "
                f"{key_title(partner)} now gives {function_text(old)}.{self._tail()}",
                actions=[("Keep both", self._keep_both), undo])
        elif change.duplicates:
            on = ", ".join(key_title(k) for k in change.duplicates)
            self.toast.show_message(
                f"<b>Remapped, no swap</b><br>{function_text(function)} is on several keys "
                f"({on}), so no key got {function_text(old)}.{self._tail()}",
                "warning", [undo])
        else:
            self.toast.show_message(
                f"<b>Remapped</b><br>{key_title(key)} now gives {function_text(function)}.{self._tail()}",
                actions=[undo])

    def _revert(self, key: str) -> None:
        self._finish(None)
        change = self.c.revert(key)
        self._flash(key, change.swapped_with)
        text = f"<b>{key_title(key)} restored</b>"
        if change.swapped_with:
            partner = change.swapped_with
            gives = keymap.function_of(change.mappings, partner)
            text += f"<br>{key_title(partner)} now gives {function_text(gives)}."
        self.toast.show_message(text + self._tail(), actions=[("Undo", self._undo)])

    def _reset_all(self) -> None:
        self._finish(None)
        self.c.reset_mappings()
        self.toast.show_message("<b>All remaps removed</b>", actions=[("Undo", self._undo)])

    def _undo(self) -> None:
        self.c.undo()
        self.toast.show_message("Change undone.")

    def _keep_both(self) -> None:
        self.c.keep_both()
        self.toast.show_message("Both keys kept: they give the same function now.")

    def _flash(self, *names: str | None) -> None:
        for name in names:
            if name in self.grid.caps:
                self.grid.caps[name].flash()

    def _on_helper(self, enabled: bool) -> None:
        self.c.set_helper(enabled)
        self.helper.blockSignals(True)
        self.helper.setChecked(self.c.helper_installed())
        self.helper.blockSignals(False)

    # ---- state -> widgets ------------------------------------------------------

    def refresh(self) -> None:
        if self._capturing and self.c.config.active_profile != self._listen_profile:
            self._finish(None)
            return
        mappings = self.c.profile.mappings
        self.grid.show_mappings(mappings, self._selected, self._capturing)
        count = len(mappings)
        self.badge.setText(f"{count} key{'s' if count != 1 else ''} remapped")
        self.badge.setVisible(count > 0)
        self._show_panel()
        self.remaps.show_mappings(mappings, self.c.config.active_profile)
        self._show_footer()

    def _show_panel(self) -> None:
        current = (keymap.function_of(self.c.profile.mappings, self._selected)
                   if self._selected else None)
        self.panel.show_key(self._selected, current, self._capturing, self._unsupported_key)

    def _show_footer(self, *_args) -> None:
        if self.c.connected:
            self.status.show_status("Remaps active on the keyboard", ok=True)
        else:
            self.status.show_status("Saved. Remaps apply when the keyboard connects.", ok=False)
