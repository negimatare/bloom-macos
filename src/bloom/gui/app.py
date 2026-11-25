"""Bloom main window."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .controller import Controller
from .keys_tab import KeysTab
from .lighting_tab import LightingTab
from .profiles_tab import ProfilesTab

APP_NAME = "Bloom"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(640, 640)
        self.c = Controller()

        title = QLabel("Razer BlackWidow Lite")
        font = title.font()
        font.setPointSize(font.pointSize() + 5)
        font.setBold(True)
        title.setFont(font)

        self.dot = QLabel("●")
        self.status = QLabel()
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.dot)
        header.addWidget(self.status)

        self.profile_label = QLabel()
        self.profile_label.setStyleSheet("color: gray;")

        tabs = QTabWidget()
        tabs.addTab(LightingTab(self.c), "Lighting")
        tabs.addTab(KeysTab(self.c), "Keys")
        tabs.addTab(ProfilesTab(self.c), "Profiles")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(header)
        layout.addWidget(self.profile_label)
        layout.addWidget(tabs, 1)
        self.setCentralWidget(central)

        self.c.connection_changed.connect(self._show_connection)
        self.c.config_changed.connect(self._show_profile)
        self.c.message.connect(lambda text: self.statusBar().showMessage(text, 5000))
        self._show_connection(self.c.connected)
        self._show_profile()

    def _show_connection(self, connected: bool) -> None:
        colour = "#3fb950" if connected else "#8b949e"
        self.dot.setStyleSheet(f"color: {colour}; font-size: 16px;")
        self.status.setText("Connected" if connected else "Not connected")

    def _show_profile(self) -> None:
        self.profile_label.setText(f"Profile: {self.c.config.active_profile}")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
