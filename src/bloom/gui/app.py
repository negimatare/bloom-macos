"""Bloom main window."""

from __future__ import annotations

import html
import subprocess
import sys

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, ICON_PNG
from . import icons, theme
from .controller import Controller
from .keymap_studio import KeymapStudio
from .lighting_studio import LightingStudio
from .profile_studio import ProfileStudio
from .widgets import Toast, label, segmented

SCREENS = [("Lighting", "sun"), ("Keymap", "keyboard"), ("Profiles", "layers")]
START_SCREEN = 0
INPUT_MONITORING_SETTINGS = "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"
PERMISSION_TEXT = (
    "<b>macOS blocks the keyboard lighting</b><br>In Privacy &amp; Security → Input Monitoring, "
    f"switch on {APP_NAME}, or the terminal that opened Bloom, then open Bloom again."
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(900, 760)
        self.c = Controller()

        logo = QLabel()
        logo.setPixmap(icons.pixmap("flower", theme.ACCENT, 20))
        nav, self.nav = segmented([name for name, _ in SCREENS], "nav")
        for (_, icon_name), button in zip(SCREENS, self.nav.buttons()):
            button.setIcon(icons.icon(icon_name, theme.MUTED, theme.ACCENT))
            button.setIconSize(QSize(15, 15))

        self.dot = QLabel("●")
        self.status = label(role="muted")
        self.profiles = QComboBox()
        self.profiles.setAccessibleName("Active profile")

        topbar = QFrame()
        topbar.setObjectName("topbar")
        bar = QHBoxLayout(topbar)
        bar.setContentsMargins(16, 10, 16, 10)
        bar.addWidget(logo)
        bar.addWidget(label(APP_NAME, "wordmark"))
        bar.addSpacing(18)
        bar.addLayout(nav)
        bar.addStretch(1)
        bar.addWidget(self.dot)
        bar.addWidget(self.status)
        bar.addSpacing(10)
        bar.addWidget(self.profiles)

        central = QWidget()
        self.toast = Toast(central)
        self.pages = QStackedWidget()
        for page in (LightingStudio(self.c), KeymapStudio(self.c, self.toast),
                     ProfileStudio(self.c, self.toast)):
            self.pages.addWidget(page)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(topbar)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(central)

        self.nav.idClicked.connect(self.pages.setCurrentIndex)
        self.nav.button(START_SCREEN).setChecked(True)
        self.pages.setCurrentIndex(START_SCREEN)
        self.profiles.activated.connect(lambda i: self.c.activate(self.profiles.itemText(i)))
        self.c.connection_changed.connect(self._show_connection)
        self.c.config_changed.connect(self._show_profiles)
        self.c.message.connect(lambda text: self.toast.show_message(html.escape(text)))
        self.c.error.connect(lambda text: self.toast.show_message(html.escape(text), "error"))
        self.c.permission_needed.connect(self._ask_permission)
        self._show_connection(self.c.connected)
        self._show_profiles()

    def _ask_permission(self) -> None:
        self.toast.show_message(PERMISSION_TEXT, "error", [("Open Settings", self._open_settings)])

    @staticmethod
    def _open_settings() -> None:
        subprocess.Popen(["/usr/bin/open", INPUT_MONITORING_SETTINGS])

    def _show_connection(self, connected: bool) -> None:
        self.dot.setStyleSheet(f"color: {theme.SUCCESS if connected else theme.MUTED};")
        self.status.setText("Connected" if connected else "Not connected")

    def _show_profiles(self) -> None:
        self.profiles.blockSignals(True)
        self.profiles.clear()
        self.profiles.addItems(list(self.c.config.profiles))
        self.profiles.setCurrentText(self.c.config.active_profile)
        self.profiles.blockSignals(False)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(str(ICON_PNG)))
    theme.apply(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
