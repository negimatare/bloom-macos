"""A drawing of the keyboard whose legends glow like the real white backlight."""

from __future__ import annotations

import math
import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from .. import layout
from ..lighting import LightEffect
from . import theme

BREATH_SECONDS = 4.0


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(*(round(x + (y - x) * t) for x, y in zip(a.getRgb()[:3], b.getRgb()[:3])))


class KeyboardPreview(QWidget):
    """The keyboard drawn with its legends lit like the real white backlight."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(190)
        self.setAccessibleName("Backlight preview")
        self._brightness = 1.0
        self._effect = LightEffect.STATIC
        self._start = time.monotonic()
        self._anim = QTimer(self)
        self._anim.timeout.connect(self.update)

    def set_state(self, effect: LightEffect, brightness_percent: int) -> None:
        self._effect = effect
        self._brightness = brightness_percent / 100
        if effect is LightEffect.BREATHING:
            self._anim.start(33)
        else:
            self._anim.stop()
        self.update()

    def _level(self) -> float:
        if self._effect is LightEffect.OFF:
            return 0.0
        if self._effect is LightEffect.BREATHING:
            phase = (time.monotonic() - self._start) % BREATH_SECONDS / BREATH_SECONDS
            return self._brightness * (0.5 - 0.5 * math.cos(2 * math.pi * phase))
        return self._brightness

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        level = self._level()

        margin = 14
        unit = min((self.width() - 2 * margin) / layout.WIDTH,
                   (self.height() - 2 * margin) / layout.HEIGHT)
        x0 = (self.width() - unit * layout.WIDTH) / 2
        y0 = (self.height() - unit * layout.HEIGHT) / 2

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#121014"))
        painter.drawRoundedRect(
            QRectF(x0 - 10, y0 - 10, unit * layout.WIDTH + 20, unit * layout.HEIGHT + 20), 12, 12
        )

        cap = QColor(theme.KEY)
        legend = _mix(QColor("#5A5360"), QColor("#FFFFFF"), level)
        glow = QColor(255, 255, 255, round(55 * level))
        font = QFont(self.font())
        font.setPixelSize(max(7, round(unit * 0.26)))
        painter.setFont(font)

        pad = unit * 0.07
        for key in layout.KEYS:
            rect = QRectF(x0 + key.x * unit + pad, y0 + key.y * unit + pad,
                          key.width * unit - 2 * pad, unit - 2 * pad)
            if level > 0:
                painter.setPen(Qt.NoPen)
                painter.setBrush(glow)
                painter.drawRoundedRect(rect.adjusted(-1.5, -1.5, 1.5, 1.5), 5, 5)
            painter.setPen(Qt.NoPen)
            painter.setBrush(cap)
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(legend)
            painter.drawText(rect, Qt.AlignCenter, key.legend)
