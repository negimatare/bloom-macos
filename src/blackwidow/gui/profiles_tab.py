"""Profiles tab: named sets of lighting + key mappings."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import hid_usages
from .controller import Controller


class ProfilesTab(QWidget):
    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self.c = controller

        intro = QLabel("A profile stores the backlight settings and key mappings. "
                       "Double-click a profile to use it.")
        intro.setWordWrap(True)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda item: self.c.activate(item.data(Qt.UserRole)))
        self.list.currentItemChanged.connect(self._show_details)

        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setStyleSheet("color: gray;")

        self.use_button = QPushButton("Use")
        new = QPushButton("New…")
        duplicate = QPushButton("Duplicate…")
        rename = QPushButton("Rename…")
        delete = QPushButton("Delete")
        self.use_button.clicked.connect(lambda: self._selected() and self.c.activate(self._selected()))
        new.clicked.connect(self._new)
        duplicate.clicked.connect(self._duplicate)
        rename.clicked.connect(self._rename)
        delete.clicked.connect(self._delete)

        buttons = QHBoxLayout()
        for b in (new, duplicate, rename, delete):
            buttons.addWidget(b)
        buttons.addStretch(1)
        buttons.addWidget(self.use_button)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.list, 1)
        layout.addWidget(self.details)
        layout.addLayout(buttons)

        self.c.config_changed.connect(self.refresh)
        self.refresh()

    def _selected(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def refresh(self) -> None:
        selected = self._selected() or self.c.config.active_profile
        self.list.blockSignals(True)
        self.list.clear()
        for name in self.c.config.profiles:
            active = name == self.c.config.active_profile
            item = QListWidgetItem(f"{name}  (in use)" if active else name)
            item.setData(Qt.UserRole, name)
            font = item.font()
            font.setBold(active)
            item.setFont(font)
            self.list.addItem(item)
            if name == selected:
                self.list.setCurrentItem(item)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        self.list.blockSignals(False)
        self._show_details()

    def _show_details(self, *_args) -> None:
        name = self._selected()
        if name is None or name not in self.c.config.profiles:
            self.details.clear()
            return
        profile = self.c.config.profiles[name]
        light = profile.lighting
        lighting = ("Backlight off" if light.effect == "off"
                    else f"{light.effect.title()} at {light.brightness}%")
        if profile.mappings:
            maps = ", ".join(f"{hid_usages.label(a)} → {hid_usages.label(b)}"
                             for a, b in profile.mappings)
        else:
            maps = "no key mappings"
        self.details.setText(f"{lighting}; {maps}")
        self.use_button.setEnabled(name != self.c.config.active_profile)

    def _ask_name(self, title: str, default: str = "") -> str | None:
        name, ok = QInputDialog.getText(self, title, "Profile name:", text=default)
        return name if ok else None

    def _new(self) -> None:
        name = self._ask_name("New profile")
        if name is not None:
            self.c.new_profile(name)

    def _duplicate(self) -> None:
        source = self._selected()
        if source is None:
            return
        name = self._ask_name("Duplicate profile", f"{source} copy")
        if name is not None:
            self.c.new_profile(name, copy_of=source)

    def _rename(self) -> None:
        old = self._selected()
        if old is None:
            return
        name = self._ask_name("Rename profile", old)
        if name is not None and name != old:
            self.c.rename_profile(old, name)

    def _delete(self) -> None:
        name = self._selected()
        if name is None:
            return
        answer = QMessageBox.question(self, "Delete profile", f"Delete the profile '{name}'?")
        if answer == QMessageBox.Yes:
            self.c.delete_profile(name)
