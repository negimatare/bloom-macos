"""Profile Studio: the profile library on the left, the selected profile on the right.

Selecting a profile only shows it; "Use profile" makes it active.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QButtonGroup, QFileDialog, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from . import icons, theme
from .controller import Controller
from .profile_detail import ProfileDetail
from .profile_widgets import ProfileDialog, ProfileItem
from .widgets import StatusLine, Toast, clear, label, text_block

EXPORT_FILTER = "Bloom profile (*.json)"


class ProfileStudio(QWidget):
    def __init__(self, controller: Controller, toast: Toast) -> None:
        super().__init__()
        self.c = controller
        self.toast = toast
        self._selected = self.c.config.active_profile

        new = QPushButton(" New")
        new.setProperty("role", "primary")
        new.setIcon(icons.icon("plus", theme.ON_ACCENT))
        new.clicked.connect(self._new)
        header = QHBoxLayout()
        header.addLayout(text_block("Your profiles", "One keyboard, many setups.", "title"), 1)
        header.addWidget(new, alignment=Qt.AlignTop)

        self.library_label = label(role="muted")
        self.items = QVBoxLayout()
        self.items.setSpacing(8)
        self.group = QButtonGroup(self)
        import_button = QPushButton(" Import profile")
        import_button.setProperty("role", "flat")
        import_button.setIcon(icons.icon("upload", theme.MUTED))
        import_button.clicked.connect(self._import)
        library = QVBoxLayout()
        library.addWidget(self.library_label)
        library.addLayout(self.items)
        library.addWidget(import_button, alignment=Qt.AlignHCenter)
        library.addStretch(1)
        library_widget = QWidget()
        library_widget.setLayout(library)
        library_widget.setFixedWidth(280)

        self.detail = ProfileDetail()
        self.detail.use_button.clicked.connect(lambda: self.c.activate(self._selected))
        self.detail.edit_button.clicked.connect(self._edit)
        self.detail.duplicate_button.clicked.connect(self._duplicate)
        self.detail.restore_button.clicked.connect(self._restore)
        self.detail.export_button.clicked.connect(self._export)
        self.detail.delete_button.clicked.connect(self._delete)

        columns = QHBoxLayout()
        columns.setSpacing(16)
        columns.addWidget(library_widget)
        columns.addWidget(self.detail, 1)

        self.status = StatusLine()
        footer = QHBoxLayout()
        footer.addWidget(self.status, 1)
        footer.addWidget(label("Stored only on this Mac", "muted"))

        page = QVBoxLayout(self)
        page.setContentsMargins(24, 20, 24, 16)
        page.setSpacing(14)
        page.addLayout(header)
        page.addLayout(columns, 1)
        page.addLayout(footer)

        self.c.config_changed.connect(self.refresh)
        self.refresh()

    # ---- state -> widgets ------------------------------------------------------

    def _select(self, name: str) -> None:
        self._selected = name
        self.refresh()

    def refresh(self) -> None:
        profiles = self.c.config.profiles
        active = self.c.config.active_profile
        if self._selected not in profiles:
            self._selected = active
        for button in self.group.buttons():
            self.group.removeButton(button)
        clear(self.items)
        for name, profile in profiles.items():
            item = ProfileItem(name, profile, name == active)
            item.setChecked(name == self._selected)
            item.clicked.connect(lambda _=False, n=name: self._select(n))
            self.group.addButton(item)
            self.items.addWidget(item)
        self.library_label.setText(f"LIBRARY · {len(profiles)}")
        self.detail.show_profile(self._selected, profiles[self._selected], self._selected == active,
                                 can_delete=len(profiles) > 1)
        self.status.show_status(f"Active profile: {active}", ok=True)

    # ---- actions ----------------------------------------------------------------

    def _ask(self, title: str, name: str, icon: str) -> tuple[str, str] | None:
        dialog = ProfileDialog(self, title, name, icon)
        return dialog.values() if dialog.exec() else None

    def _new(self) -> None:
        answer = self._ask("New profile", self.c.config.free_name("New profile"), "keyboard")
        if answer and (name := self.c.new_profile(*answer)):
            self._select(name)
            self.toast.show_message(f"Profile '{name}' created.")

    def _edit(self) -> None:
        profile = self.c.config.profiles[self._selected]
        answer = self._ask("Edit profile", self._selected, profile.icon)
        if answer and (name := self.c.edit_profile(self._selected, *answer)):
            self._select(name)
            self.toast.show_message("Profile saved.")

    def _duplicate(self) -> None:
        source = self._selected
        icon = self.c.config.profiles[source].icon
        name = self.c.new_profile(self.c.config.free_name(f"{source} copy"), icon, copy_of=source)
        if name:
            self._select(name)
            self.toast.show_message(f"Profile '{name}' created from '{source}'.")

    def _restore(self) -> None:
        name = self._selected
        self.c.restore_default(name)
        self.toast.show_message(
            f"<b>{name} restored to default</b><br>No remaps, static light at 100%.",
            actions=[("Undo", self._undo)])

    def _delete(self) -> None:
        name = self._selected
        if self.c.delete_profile(name):
            self.toast.show_message(f"<b>Profile '{name}' deleted</b>", actions=[("Undo", self._undo)])

    def _undo(self) -> None:
        self.c.undo()
        self.toast.show_message("Change undone.")

    def _export(self) -> None:
        name = self._selected
        path, _ = QFileDialog.getSaveFileName(
            self, "Export profile", str(Path.home() / f"{name}.json"), EXPORT_FILTER)
        if path and self.c.export_profile(name, path):
            self.toast.show_message(f"Profile '{name}' exported to {Path(path).name}.")

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import profile", str(Path.home()), EXPORT_FILTER)
        if path and (name := self.c.import_profile(path)):
            self._select(name)
            self.toast.show_message(f"Profile '{name}' imported.")
