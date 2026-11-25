"""Parts of the Profile Studio: a profile in the list, and the name-and-icon dialog."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ..config import PROFILE_ICONS, Profile
from ..lighting import LightEffect
from . import icons, theme
from .widgets import count_text, label, segmented

ICON_BOX = 32


def summary(profile: Profile) -> str:
    """ "2 remaps · 70%", "No remaps · Off" """
    count = len(profile.mappings)
    remaps = "No remaps" if count == 0 else count_text(count, "remap")
    light = profile.lighting
    if light.effect == LightEffect.OFF.value:
        level = "Off"
    else:
        level = f"{light.brightness}%" + (" breathing" if light.effect == LightEffect.BREATHING.value else "")
    return f"{remaps} · {level}"


class ProfileItem(QAbstractButton):
    """One profile in the library: icon, name, summary, and a check when active."""

    def __init__(self, name: str, profile: Profile, active: bool) -> None:
        super().__init__()
        self.name = name
        self.profile = profile
        self.active = active
        self.subtitle = ("Active · " if active else "") + summary(profile)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)
        self.setAccessibleName(f"{name}, {self.subtitle}")

    def sizeHint(self) -> QSize:
        return QSize(240, 58)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        selected = self.isChecked()
        border = theme.ACCENT if selected else (theme.MUTED if self.underMouse() else theme.BORDER)
        painter.setPen(QPen(QColor(border), 1))
        painter.setBrush(QColor(theme.REMAPPED if selected else theme.PANEL))
        painter.drawRoundedRect(rect, 10, 10)

        box = QRectF(rect.left() + 10, rect.center().y() - ICON_BOX / 2, ICON_BOX, ICON_BOX)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(theme.KEY))
        painter.drawRoundedRect(box, 8, 8)
        painter.drawPixmap(box.adjusted(8, 8, -8, -8).toRect(),
                           icons.pixmap(self.profile.icon, theme.ACCENT if selected else theme.TEXT))

        text_left = box.right() + 12
        font = QFont(self.font())
        font.setPixelSize(13)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(theme.TEXT))
        painter.drawText(QRectF(text_left, rect.top() + 9, rect.width() - text_left - 34, 20),
                         Qt.AlignLeft | Qt.AlignVCenter, self.name)
        font.setPixelSize(11)
        font.setWeight(QFont.Normal)
        painter.setFont(font)
        painter.setPen(QColor(theme.MUTED))
        painter.drawText(QRectF(text_left, rect.top() + 29, rect.width() - text_left - 34, 18),
                         Qt.AlignLeft | Qt.AlignVCenter, self.subtitle)
        if self.active:
            check = QRectF(rect.right() - 28, rect.center().y() - 8, 16, 16)
            painter.drawPixmap(check.toRect(), icons.pixmap("circle-check", theme.ACCENT))


class ProfileDialog(QDialog):
    """Ask for a profile name and an icon."""

    def __init__(self, parent, title: str, name: str, icon: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(380)
        self.name_edit = QLineEdit(name)
        self.name_edit.setAccessibleName("Profile name")
        self.name_edit.selectAll()
        self.name_edit.setStyleSheet(
            f"background: {theme.PANEL}; border: 1px solid {theme.BORDER_STRONG};"
            " border-radius: 8px; padding: 6px 8px;")
        icon_row, self.icon_group = segmented([""] * len(PROFILE_ICONS), "segment")
        for button, icon_name in zip(self.icon_group.buttons(), PROFILE_ICONS):
            button.setIcon(icons.icon(icon_name, theme.MUTED, theme.ACCENT))
            button.setIconSize(QSize(16, 16))
            button.setAccessibleName(icon_name.replace("-2", "").replace("-", " "))
        self.icon_group.button(PROFILE_ICONS.index(icon)).setChecked(True)

        cancel = QPushButton("Cancel")
        save = QPushButton("Save")
        save.setProperty("role", "primary")
        save.setDefault(True)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(save)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        layout.addWidget(label("Name", "heading"))
        layout.addWidget(self.name_edit)
        layout.addWidget(label("Icon", "heading"))
        layout.addLayout(icon_row)
        layout.addSpacing(6)
        layout.addLayout(buttons)

    def values(self) -> tuple[str, str]:
        return self.name_edit.text(), PROFILE_ICONS[self.icon_group.checkedId()]
