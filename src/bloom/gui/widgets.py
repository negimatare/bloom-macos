"""Small building blocks shared by the Bloom screens."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme

TOAST_MS = 5000
ERROR_TOAST_MS = 9000


def label(text: str = "", role: str | None = None) -> QLabel:
    widget = QLabel(text)
    if role:
        widget.setProperty("role", role)
    return widget


def text_block(heading: str, detail: str, heading_role: str = "heading") -> QVBoxLayout:
    block = QVBoxLayout()
    block.setSpacing(2)
    block.addWidget(label(heading, heading_role))
    block.addWidget(label(detail, "muted"))
    return block


def card() -> QFrame:
    frame = QFrame()
    frame.setProperty("role", "card")
    return frame


def separator() -> QFrame:
    line = QFrame()
    line.setProperty("role", "separator")
    return line


def segmented(labels: list[str], role: str) -> tuple[QHBoxLayout, QButtonGroup]:
    """A row of exclusive, checkable buttons; the group's ids follow `labels`."""
    row = QHBoxLayout()
    row.setSpacing(4)
    group = QButtonGroup(row)
    for i, text in enumerate(labels):
        button = QPushButton(text)
        button.setCheckable(True)
        button.setProperty("role", role)
        button.setCursor(Qt.PointingHandCursor)
        group.addButton(button, i)
        row.addWidget(button)
    return row, group


class ToggleSwitch(QAbstractButton):
    """An on/off pill switch."""

    def __init__(self, accessible_name: str) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName(accessible_name)

    def sizeHint(self) -> QSize:
        return QSize(42, 24)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track = QRectF(0, 0, 42, 24).translated(0, (self.height() - 24) / 2)
        on = self.isChecked()
        colour = theme.ACCENT if on else theme.KEY
        if not self.isEnabled():
            colour = theme.DISABLED
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(colour))
        painter.drawRoundedRect(track, 12, 12)
        knob_x = track.right() - 21 if on else track.left() + 3
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(knob_x, track.top() + 3, 18, 18))


class Toast(QFrame):
    """A short, non-blocking notice at the bottom of its parent window."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"Toast {{ background: #2D2730; border: 1px solid {theme.REMAPPED}; border-radius: 10px; }}"
            " Toast QLabel { background: transparent; }"
        )
        self._icon = QLabel()
        self._text = QLabel()
        self._text.setWordWrap(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.addWidget(self._icon)
        layout.addWidget(self._text, 1)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        parent.installEventFilter(self)
        self.hide()

    def show_message(self, text: str, error: bool = False) -> None:
        name, colour = ("circle-alert", theme.ERROR) if error else ("circle-check", theme.SUCCESS)
        self._icon.setPixmap(icons.pixmap(name, colour))
        self._text.setText(text)
        self.setAccessibleName(text)
        self._place()
        self.show()
        self.raise_()
        self._timer.start(ERROR_TOAST_MS if error else TOAST_MS)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Resize and self.isVisible():
            self._place()
        return False

    def _place(self) -> None:
        parent = self.parentWidget()
        width = min(480, parent.width() - 40)
        self.setFixedWidth(width)
        self.adjustSize()
        self.move((parent.width() - width) // 2, parent.height() - self.height() - 20)
