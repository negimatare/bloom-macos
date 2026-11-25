"""Small building blocks shared by the Bloom screens."""

from __future__ import annotations

import re
from collections.abc import Callable

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
LONG_TOAST_MS = 9000


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


class StatusLine(QWidget):
    """A small check icon and muted text: green when the change reached the keyboard."""

    def __init__(self) -> None:
        super().__init__()
        self._icon = QLabel()
        self._text = label(role="muted")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._icon)
        row.addWidget(self._text, 1)

    def show_status(self, text: str, ok: bool) -> None:
        self._icon.setPixmap(icons.pixmap("circle-check", theme.SUCCESS if ok else theme.MUTED, 14))
        self._text.setText(text)


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

    KINDS = {
        "success": ("circle-check", theme.SUCCESS),
        "warning": ("circle-alert", theme.ACCENT),
        "error": ("circle-alert", theme.ERROR),
    }

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"Toast {{ background: #2D2730; border: 1px solid {theme.REMAPPED}; border-radius: 10px; }}"
            " Toast QLabel { background: transparent; }"
        )
        self._icon = QLabel()
        self._text = QLabel()
        self._text.setWordWrap(True)
        self._actions = QHBoxLayout()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.addWidget(self._icon, alignment=Qt.AlignTop)
        layout.addWidget(self._text, 1)
        layout.addLayout(self._actions)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        parent.installEventFilter(self)
        self.hide()

    def show_message(self, text: str, kind: str = "success",
                     actions: list[tuple[str, Callable[[], None]]] = ()) -> None:
        """`text` may use simple HTML; each action is a button that runs and closes."""
        name, colour = self.KINDS[kind]
        self._icon.setPixmap(icons.pixmap(name, colour))
        self._text.setText(text)
        self.setAccessibleName(re.sub(r"<[^>]+>", " ", text))
        while self._actions.count():
            self._actions.takeAt(0).widget().deleteLater()
        for i, (caption, run) in enumerate(actions):
            button = QPushButton(caption)
            button.setCursor(Qt.PointingHandCursor)
            if i == len(actions) - 1:
                button.setProperty("role", "primary")
            button.clicked.connect(lambda _=False, run=run: (self.hide(), run()))
            self._actions.addWidget(button)
        self._place()
        self.show()
        self.raise_()
        self._timer.start(LONG_TOAST_MS if kind == "error" or actions else TOAST_MS)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Resize and self.isVisible():
            self._place()
        return False

    def _place(self) -> None:
        parent = self.parentWidget()
        width = min(560, parent.width() - 40)
        self.setFixedWidth(width)
        self.adjustSize()
        self.move((parent.width() - width) // 2, parent.height() - self.height() - 20)
