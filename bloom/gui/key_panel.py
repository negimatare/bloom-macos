"""The panel under the keyboard: a hint, or the wait for the next key press."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from . import icons, theme
from .keycaps import function_text, key_title
from .widgets import label


class KeyPanel(QFrame):
    cancel_clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setProperty("role", "card")
        self.icon = QLabel()
        self.icon.setPixmap(icons.pixmap("radio", theme.ACCENT, 22))
        self.title = label(role="heading")
        self.detail = label(role="muted")
        self.detail.setWordWrap(True)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_clicked)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(self.title)
        text.addWidget(self.detail)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)
        row.addWidget(self.icon)
        row.addLayout(text, 1)
        row.addWidget(self.cancel_button)

    def show_key(self, listening_key: str | None, current: str | None, unsupported_key: bool) -> None:
        listening = listening_key is not None
        self.setProperty("active", listening)
        self.style().unpolish(self)
        self.style().polish(self)
        self.cancel_button.setVisible(listening)
        self.icon.setVisible(listening)
        self.title.setStyleSheet(f"color: {theme.ACCENT};" if listening else "")
        if not listening:
            self.title.setText("Click a key to remap it")
            self.detail.setText(
                "Then press the key it should become. Escape, Tab and Return count as keys too.")
        else:
            self.title.setText("Waiting for a key…")
            self.detail.setText(
                "That key can't be remapped. Press another key, or click Cancel."
                if unsupported_key else
                f"Press the key {key_title(listening_key)} should become. "
                f"Current: {function_text(current)}")
