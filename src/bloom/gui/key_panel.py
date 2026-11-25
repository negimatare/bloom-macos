"""The panel under the keyboard: the selected key, or the wait for a key press."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .. import layout
from . import icons, theme
from .keycaps import KeyCap, function_text, key_title
from .widgets import label

CAP_SIZE = 58


class KeyPanel(QFrame):
    remap_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setProperty("role", "card")
        self.cap = KeyCap(layout.KEYS[0])
        self.cap.setFixedSize(CAP_SIZE, CAP_SIZE)
        self.cap.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.cap.setFocusPolicy(Qt.NoFocus)
        self.icon = QLabel()
        self.icon.setPixmap(icons.pixmap("radio", theme.ACCENT, 22))
        self.title = label(role="heading")
        self.detail = label(role="muted")
        self.detail.setWordWrap(True)
        self.remap_button = QPushButton("Remap")
        self.cancel_button = QPushButton("Cancel")
        self.remap_button.clicked.connect(self.remap_clicked)
        self.cancel_button.clicked.connect(self.cancel_clicked)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(self.title)
        text.addWidget(self.detail)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)
        row.addWidget(self.cap)
        row.addWidget(self.icon)
        row.addLayout(text, 1)
        row.addWidget(self.remap_button)
        row.addWidget(self.cancel_button)

    def show_key(self, key: str | None, current: str | None, listening: bool,
                 unsupported_key: bool) -> None:
        self.setProperty("active", listening)
        self.style().unpolish(self)
        self.style().polish(self)
        self.remap_button.setVisible(key is not None and not listening)
        self.cancel_button.setVisible(listening)
        self.icon.setVisible(listening)
        self.cap.setVisible(key is not None and not listening)
        self.title.setStyleSheet(f"color: {theme.ACCENT};" if listening else "")
        if key is None:
            self.title.setText("Click a key to remap it")
            self.detail.setText(
                "Then press the key it should become. Escape, Tab and Return count as keys too.")
        elif listening:
            self.title.setText("Waiting for a key…")
            self.detail.setText(
                "That key can't be remapped. Press another key, or click Cancel."
                if unsupported_key else
                f"Press the key {key_title(key)} should become. Current: {function_text(current)}")
        else:
            self.cap.key = layout.BY_NAME[key]
            self.cap.set_state(current, True, False)
            self.title.setText(key_title(key))
            self.detail.setText(f"Gives {function_text(current)}")
