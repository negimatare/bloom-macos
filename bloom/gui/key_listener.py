"""Catch the next key press anywhere in the app, before Qt uses it for shortcuts."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QWidget

from .. import mac_keycodes


class KeyListener(QObject):
    captured = Signal(str)  # key name
    unsupported = Signal()
    clicked_outside = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._inside: tuple[QWidget, ...] = ()

    def start(self, *inside: QWidget) -> None:
        """Listen until `stop`; a click on none of the `inside` widgets is a click outside."""
        self._inside = inside
        QApplication.instance().installEventFilter(self)

    def stop(self) -> None:
        QApplication.instance().removeEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        kind = event.type()
        if kind == QEvent.ShortcutOverride:
            event.accept()
            return True
        if kind == QEvent.KeyPress:
            if not event.isAutoRepeat():
                name = mac_keycodes.name_for_virtual_key(event.nativeVirtualKey())
                if name is None:
                    self.unsupported.emit()
                else:
                    self.captured.emit(name)
            return True
        if kind == QEvent.KeyRelease:
            return True
        if kind == QEvent.MouseButtonPress and not self._under_cursor():
            self.clicked_outside.emit()
        return False

    def _under_cursor(self) -> bool:
        pos = QCursor.pos()
        return any(w.isVisible() and w.rect().contains(w.mapFromGlobal(pos)) for w in self._inside)
