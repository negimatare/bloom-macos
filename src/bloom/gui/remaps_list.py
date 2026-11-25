"""The collapsible list of active remaps, each with its own restore button."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import icons, theme
from .keycaps import function_text, key_title
from .widgets import label, separator


class RemapsList(QFrame):
    revert_clicked = Signal(str)  # key name
    reset_clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.toggle = QPushButton("Active remaps")
        self.toggle.setProperty("role", "flat-heading")
        self.toggle.setCheckable(True)
        self.toggle.setChecked(True)
        self.toggle.setIconSize(QSize(14, 14))
        self.toggle.toggled.connect(self._show_open)
        self.count = label(role="muted")
        remaps_header = QHBoxLayout()
        remaps_header.addWidget(self.toggle)
        remaps_header.addStretch(1)
        remaps_header.addWidget(self.count)
        self.body = QWidget()
        self.rows = QVBoxLayout(self.body)
        self.rows.setContentsMargins(0, 0, 0, 0)
        self.rows.setSpacing(0)
        self.profile_label = label(role="muted")
        self.reset_button = QPushButton("Reset all")
        self.reset_button.setProperty("role", "flat")
        self.reset_button.clicked.connect(self.reset_clicked)
        remaps_footer = QHBoxLayout()
        remaps_footer.addWidget(self.profile_label, 1)
        remaps_footer.addWidget(self.reset_button)
        self.setProperty("role", "card")
        remaps_layout = QVBoxLayout(self)
        remaps_layout.setContentsMargins(16, 10, 16, 10)
        remaps_layout.addLayout(remaps_header)
        remaps_layout.addWidget(self.body)
        remaps_layout.addWidget(separator())
        remaps_layout.addLayout(remaps_footer)

    def show_mappings(self, mappings: list[tuple[str, str]], profile: str) -> None:
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        for src, dst in mappings:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 6, 0, 6)
            row_layout.addWidget(QLabel(key_title(src)), 1)
            target = QLabel(f"→ {function_text(dst)}")
            target.setStyleSheet(f"color: {theme.ACCENT};")
            row_layout.addWidget(target)
            revert = QPushButton()
            revert.setProperty("role", "flat")
            revert.setIcon(icons.icon("rotate-ccw", theme.MUTED))
            revert.setCursor(Qt.PointingHandCursor)
            revert.setToolTip(f"Restore {key_title(src)}")
            revert.setAccessibleName(f"Restore {key_title(src)}")
            revert.clicked.connect(lambda _=False, key=src: self.revert_clicked.emit(key))
            row_layout.addWidget(revert)
            self.rows.addWidget(row)
        if not mappings:
            self.rows.addWidget(label("No remaps. Every key gives its own function.", "muted"))
        count = len(mappings)
        self.count.setText(f"{count} remap{'s' if count != 1 else ''}")
        self.profile_label.setText(f"Profile: {profile}")
        self.reset_button.setEnabled(count > 0)
        self._show_open(self.toggle.isChecked())

    def _show_open(self, open_: bool) -> None:
        self.body.setVisible(open_)
        self.toggle.setIcon(icons.icon("chevron-down" if open_ else "chevron-right", theme.MUTED))
