"""The right side of the Profile Studio: what the selected profile holds, and its actions."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from ..config import Profile
from ..lighting import LightEffect
from . import icons, theme
from .keycaps import function_text, key_title
from .profile_widgets import summary
from .widgets import clear, count_text, label, separator


def _icon_button(icon: str, text: str) -> QPushButton:
    button = QPushButton()
    button.setProperty("role", "flat")
    button.setIcon(icons.icon(icon, theme.MUTED))
    button.setIconSize(QSize(16, 16))
    button.setCursor(Qt.PointingHandCursor)
    button.setToolTip(text)
    button.setAccessibleName(text)
    return button


def _row_title(icon: str, text: str) -> QHBoxLayout:
    image = QLabel()
    image.setPixmap(icons.pixmap(icon, theme.MUTED))
    row = QHBoxLayout()
    row.addWidget(image)
    row.addWidget(label(text, "heading"), 1)
    return row


def _stack(*widgets: QWidget) -> QVBoxLayout:
    stack = QVBoxLayout()
    stack.setSpacing(2)
    for w in widgets:
        stack.addWidget(w)
    return stack


class ProfileDetail(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.icon_box = QLabel()
        self.icon_box.setFixedSize(48, 48)
        self.icon_box.setAlignment(Qt.AlignCenter)
        self.icon_box.setStyleSheet(f"background: {theme.REMAPPED}; border-radius: 12px;")
        self.name = label(role="title")
        self.subtitle = label(role="muted")
        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(self.icon_box)
        top.addLayout(_stack(self.name, self.subtitle), 1)

        self.light_value = label(role="value")
        lighting_row = _row_title("sun", "Lighting")
        lighting_row.addWidget(self.light_value)
        self.light_bar = QProgressBar()
        self.light_bar.setRange(0, 100)
        self.light_bar.setTextVisible(False)
        self.light_bar.setAccessibleName("Brightness")

        self.remaps_value = label(role="muted")
        remaps_row = _row_title("keyboard", "Remaps")
        remaps_row.addWidget(self.remaps_value)
        self.remap_lines = QVBoxLayout()
        self.remap_lines.setSpacing(4)

        self.use_button = QPushButton("Use profile")
        self.use_button.setProperty("role", "primary")
        self.edit_button = _icon_button("pencil", "Edit name and icon")
        self.duplicate_button = _icon_button("copy", "Duplicate")
        self.restore_button = _icon_button("rotate-ccw", "Restore to default")
        self.export_button = _icon_button("download", "Export")
        self.delete_button = _icon_button("trash-2", "Delete")
        actions = QHBoxLayout()
        actions.addStretch(1)
        for button in (self.edit_button, self.duplicate_button, self.restore_button,
                       self.export_button, self.delete_button):
            actions.addWidget(button)
        actions.addStretch(1)

        self.setProperty("role", "card")
        detail_layout = QVBoxLayout(self)
        detail_layout.setContentsMargins(20, 18, 20, 16)
        detail_layout.setSpacing(12)
        detail_layout.addLayout(top)
        detail_layout.addWidget(separator())
        detail_layout.addLayout(lighting_row)
        detail_layout.addWidget(self.light_bar)
        detail_layout.addWidget(separator())
        detail_layout.addLayout(remaps_row)
        detail_layout.addLayout(self.remap_lines)
        detail_layout.addWidget(separator())
        detail_layout.addWidget(self.use_button)
        detail_layout.addLayout(actions)
        detail_layout.addStretch(1)

    def show_profile(self, name: str, profile: Profile, active: bool, can_delete: bool) -> None:
        self.icon_box.setPixmap(icons.pixmap(profile.icon, theme.ACCENT, 24))
        self.name.setText(name)
        self.subtitle.setText(("Active · " if active else "") + summary(profile))
        light = profile.lighting
        lit = light.effect != LightEffect.OFF.value
        self.light_value.setText(f"{light.brightness}%" if lit else "Off")
        self.light_bar.setValue(light.brightness if lit else 0)
        count = len(profile.mappings)
        self.remaps_value.setText(count_text(count, "key"))
        clear(self.remap_lines)
        for src, dst in profile.mappings:
            line = QWidget()
            row = QHBoxLayout(line)
            row.setContentsMargins(26, 0, 0, 0)
            row.addWidget(label(key_title(src), "muted"), 1)
            row.addWidget(label(f"→ {function_text(dst)}", "accent"))
            self.remap_lines.addWidget(line)
        if not profile.mappings:
            line = label("Every key gives its own function.", "muted")
            line.setContentsMargins(26, 0, 0, 0)
            self.remap_lines.addWidget(line)
        self.use_button.setEnabled(not active)
        self.use_button.setText("✓ Active profile" if active else "Use profile")
        self.delete_button.setEnabled(can_delete)
