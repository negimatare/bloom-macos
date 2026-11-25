from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from bloom.gui.key_listener import KeyListener

ESCAPE_VK = 0x35
UNKNOWN_VK = 0x48


def _press(listener: KeyListener, virtual_key: int) -> bool:
    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier, 0, virtual_key, 0)
    return listener.eventFilter(None, event)


def test_a_key_press_is_captured_by_name_and_consumed(qt_app):
    listener = KeyListener()
    captured = []
    listener.captured.connect(captured.append)
    assert _press(listener, ESCAPE_VK) is True
    assert captured == ["escape"]


def test_an_unknown_key_is_reported_and_not_captured(qt_app):
    listener = KeyListener()
    captured, unsupported = [], []
    listener.captured.connect(captured.append)
    listener.unsupported.connect(lambda: unsupported.append(True))
    _press(listener, UNKNOWN_VK)
    assert captured == []
    assert unsupported == [True]
