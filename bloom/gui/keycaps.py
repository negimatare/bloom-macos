"""The virtual keyboard of the Keymap Studio: one button per physical key."""

from __future__ import annotations

import math
import time

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QWidget

from .. import hid_usages, keymap, layout
from . import theme

PULSE_SECONDS = 1.2
FLASH_SECONDS = 0.7
FRAME_MS = 33
UNIT = 44  # pixels per key unit
FN_TOOLTIP = "Fn is handled inside the keyboard, so macOS never sees it and it can't be remapped."


def function_text(name: str) -> str:
    """A function for people: "⌘ Left Command", "Escape", "F13"."""
    short, plain = hid_usages.short_label(name), hid_usages.label(name).split(" (")[0]
    return plain if short == plain or short[0].isalnum() else f"{short} {plain}"


def key_title(name: str) -> str:
    """A physical key for people: "Left Alt", or the key label when it is not on the Razer."""
    key = layout.BY_NAME.get(name)
    return key.title if key else hid_usages.label(name)


class KeyCap(QAbstractButton):
    """A key that shows its Razer legend and the function it gives now."""

    def __init__(self, key: layout.Key, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.key = key
        self.function = key.name
        self.listening = False
        self._flash_start = -1.0
        self._frames = QTimer(self)
        self._frames.timeout.connect(self._tick)
        self.setAttribute(Qt.WA_Hover)
        if key.name is None:
            self.setToolTip(FN_TOOLTIP)
            self.setAccessibleName(f"{key.legend}, cannot be remapped")
        else:
            self.setCursor(Qt.PointingHandCursor)

    @property
    def remapped(self) -> bool:
        return self.key.name is not None and self.function != self.key.name

    def set_state(self, function: str | None, listening: bool) -> None:
        self.function, self.listening = function, listening
        if self.key.name is not None:
            gives = function_text(function)
            self.setAccessibleName(f"{self.key.title}, gives {gives}")
            self.setToolTip(f"{self.key.title} → {gives}" if self.remapped else self.key.title)
        self._animate()
        self.update()

    def flash(self) -> None:
        self._flash_start = time.monotonic()
        self._animate()

    def _flash_level(self) -> float:
        elapsed = time.monotonic() - self._flash_start
        return max(0.0, 1 - elapsed / FLASH_SECONDS) if self._flash_start >= 0 else 0.0

    def _animate(self) -> None:
        if self.listening or self._flash_level() > 0:
            self._frames.start(FRAME_MS)
        else:
            self._frames.stop()

    def _tick(self) -> None:
        self._animate()
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)

        if self.key.name is None:
            fill, border, text = theme.BACKGROUND, theme.BORDER, theme.DISABLED
        elif self.remapped or self.listening:
            fill, border, text = theme.REMAPPED, theme.REMAPPED_BORDER, theme.TEXT
        else:
            fill, border, text = theme.KEY, theme.BORDER_STRONG, theme.TEXT
        if self.underMouse() and self.key.name is not None and not self.listening:
            border = theme.MUTED
        fill_colour = QColor(fill)
        flash = self._flash_level()
        if flash:
            accent = QColor(theme.ACCENT)
            fill_colour = QColor(*(round(a + (b - a) * flash) for a, b in
                                   zip(fill_colour.getRgb()[:3], accent.getRgb()[:3])))
        pen = QPen(QColor(border), 1)
        if self.listening:
            phase = (time.monotonic() % PULSE_SECONDS) / PULSE_SECONDS
            glow = QColor(theme.ACCENT)
            glow.setAlphaF(0.45 + 0.55 * (0.5 + 0.5 * math.sin(2 * math.pi * phase)))
            pen = QPen(glow, 2.5)
        painter.setPen(pen)
        painter.setBrush(fill_colour)
        painter.drawRoundedRect(rect, 6, 6)

        font = QFont(self.font())
        unit = self.height()
        if self.remapped or self.listening:
            font.setPixelSize(max(7, round(unit * 0.2)))
            painter.setFont(font)
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(rect.adjusted(5, 3, -3, -3), Qt.AlignLeft | Qt.AlignTop, self.key.legend)
            font.setPixelSize(max(10, round(unit * 0.36)))
            font.setWeight(QFont.DemiBold)
            painter.setFont(font)
            painter.setPen(QColor(text))
            centre = hid_usages.short_label(self.function) if self.function else self.key.legend
            painter.drawText(rect.adjusted(0, unit * 0.12, 0, 0), Qt.AlignCenter, centre)
        else:
            font.setPixelSize(max(8, round(unit * (0.3 if len(self.key.legend) <= 2 else 0.22))))
            painter.setFont(font)
            painter.setPen(QColor(text))
            painter.drawText(rect, Qt.AlignCenter, self.key.legend)


class KeyboardGrid(QWidget):
    """Places one KeyCap per layout key, centred in its width."""

    key_clicked = Signal(object)  # the layout.Key

    def __init__(self) -> None:
        super().__init__()
        self.caps: dict[str | None, KeyCap] = {}
        self._all: list[KeyCap] = []
        for key in layout.KEYS:
            cap = KeyCap(key, self)
            cap.clicked.connect(lambda _=False, k=key: self.key_clicked.emit(k))
            self._all.append(cap)
            if key.name:
                self.caps[key.name] = cap
        self.setMinimumWidth(math.ceil(UNIT * layout.WIDTH))
        self.setFixedHeight(math.ceil(UNIT * layout.HEIGHT))

    def show_mappings(self, mappings: list[tuple[str, str]], listening_key: str | None) -> None:
        for cap in self._all:
            name = cap.key.name
            function = keymap.function_of(mappings, name) if name else None
            cap.set_state(function, name is not None and name == listening_key)

    def resizeEvent(self, _event) -> None:
        unit = UNIT
        x0 = (self.width() - unit * layout.WIDTH) / 2
        gap = unit * 0.06
        for cap in self._all:
            k = cap.key
            cap.setGeometry(round(x0 + k.x * unit + gap), round(k.y * unit + gap),
                            round(k.width * unit - 2 * gap), round(unit - 2 * gap))
