"""Lighting tab: backlight on/off, brightness and effect."""

from __future__ import annotations

import math
import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..lighting import LightEffect
from .controller import Controller

DEBOUNCE_MS = 150

# Tenkeyless main block: key widths in units, per row.
_ROWS = [
    [1, 0.5, 1, 1, 1, 1, 0.5, 1, 1, 1, 1, 0.5, 1, 1, 1, 1],  # 0.5 = gap
    [1] * 13 + [2],
    [1.5] + [1] * 12 + [1.5],
    [1.75] + [1] * 11 + [2.25],
    [2.25] + [1] * 10 + [2.75],
    [1.25, 1.25, 1.25, 6.25, 1.25, 1.25, 1.25, 1.25],
]
_GAPS = {(0, 1), (0, 6), (0, 11)}


class KeyboardPreview(QWidget):
    """A drawing of the keyboard whose keys glow like the real backlight."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(170)
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
            phase = (time.monotonic() - self._start) % 4.0 / 4.0
            return self._brightness * (0.5 - 0.5 * math.cos(2 * math.pi * phase))
        return self._brightness

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        level = self._level()

        units_w, units_h = 15.0, len(_ROWS) + 0.25  # extra gap under F-row
        margin = 14
        unit = min((self.width() - 2 * margin) / units_w, (self.height() - 2 * margin) / units_h)
        x0 = (self.width() - unit * units_w) / 2
        y0 = (self.height() - unit * units_h) / 2

        case = QRectF(x0 - 8, y0 - 8, unit * units_w + 16, unit * units_h + 16)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(28, 30, 36))
        painter.drawRoundedRect(case, 12, 12)

        off, lit = QColor(58, 62, 72), QColor(235, 240, 255)
        key = QColor(
            round(off.red() + (lit.red() - off.red()) * level),
            round(off.green() + (lit.green() - off.green()) * level),
            round(off.blue() + (lit.blue() - off.blue()) * level),
        )
        glow = QColor(255, 255, 255, round(70 * level))

        pad = unit * 0.08
        for r, row in enumerate(_ROWS):
            x = x0
            y = y0 + r * unit + (unit * 0.25 if r > 0 else 0)
            for c, w in enumerate(row):
                if (r, c) in _GAPS:
                    x += w * unit
                    continue
                rect = QRectF(x + pad, y + pad, w * unit - 2 * pad, unit - 2 * pad)
                if level > 0:
                    painter.setBrush(glow)
                    painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 6, 6)
                painter.setBrush(key)
                painter.drawRoundedRect(rect, 5, 5)
                x += w * unit


class LightingTab(QWidget):
    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self.c = controller

        self.preview = KeyboardPreview()

        self.on = QCheckBox("Backlight on")

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.value_label = QLabel()
        self.value_label.setMinimumWidth(44)
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.static = QRadioButton("Static")
        self.breathing = QRadioButton("Breathing")
        self.effects = QButtonGroup(self)
        self.effects.addButton(self.static)
        self.effects.addButton(self.breathing)

        brightness_row = QHBoxLayout()
        brightness_row.addWidget(QLabel("Brightness"))
        brightness_row.addWidget(self.slider, 1)
        brightness_row.addWidget(self.value_label)

        effect_box = QGroupBox("Effect")
        effect_layout = QVBoxLayout(effect_box)
        effect_layout.addWidget(self.static)
        effect_layout.addWidget(self.breathing)
        note = QLabel("This keyboard has a single white backlight zone. "
                      "Reactive, starlight and colour effects aren't supported by its firmware.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray;")
        effect_layout.addWidget(note)

        backlight_box = QGroupBox("Backlight")
        backlight_layout = QVBoxLayout(backlight_box)
        backlight_layout.addWidget(self.on)
        backlight_layout.addLayout(brightness_row)

        layout = QVBoxLayout(self)
        layout.addWidget(self.preview)
        layout.addWidget(backlight_box)
        layout.addWidget(effect_box)
        layout.addStretch(1)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(DEBOUNCE_MS)
        self._debounce.timeout.connect(self._commit_brightness)

        self.on.toggled.connect(self._on_toggled)
        self.slider.valueChanged.connect(self._on_slider)
        self.slider.sliderReleased.connect(self._commit_brightness)
        self.static.toggled.connect(lambda checked: checked and self._on_effect(LightEffect.STATIC))
        self.breathing.toggled.connect(lambda checked: checked and self._on_effect(LightEffect.BREATHING))
        self.c.config_changed.connect(self.refresh)

        self.refresh()

    # ---- state -> widgets ----------------------------------------------------

    def refresh(self) -> None:
        light = self.c.profile.lighting
        effect = LightEffect(light.effect)
        widgets = (self.on, self.slider, self.static, self.breathing)
        for w in widgets:
            w.blockSignals(True)
        self.on.setChecked(effect is not LightEffect.OFF)
        if not self._debounce.isActive():
            self.slider.setValue(light.brightness)
        if effect is LightEffect.BREATHING:
            self.breathing.setChecked(True)
        elif effect is LightEffect.STATIC:
            self.static.setChecked(True)
        elif self.effects.checkedButton() is None:
            self.static.setChecked(True)  # what "on" will restore
        for w in widgets:
            w.blockSignals(False)
        lit = effect is not LightEffect.OFF
        self.slider.setEnabled(lit)
        self.static.setEnabled(lit)
        self.breathing.setEnabled(lit)
        self.value_label.setText(f"{self.slider.value()}%")
        self.preview.set_state(effect, self.slider.value())

    # ---- widgets -> keyboard -------------------------------------------------

    def _selected_effect(self) -> LightEffect:
        return LightEffect.BREATHING if self.breathing.isChecked() else LightEffect.STATIC

    def _on_toggled(self, checked: bool) -> None:
        self.c.set_effect(self._selected_effect() if checked else LightEffect.OFF)

    def _on_effect(self, effect: LightEffect) -> None:
        if self.on.isChecked():
            self.c.set_effect(effect)

    def _on_slider(self, value: int) -> None:
        self.value_label.setText(f"{value}%")
        self.preview.set_state(self._current_effect(), value)
        self._debounce.start()

    def _current_effect(self) -> LightEffect:
        return self._selected_effect() if self.on.isChecked() else LightEffect.OFF

    def _commit_brightness(self) -> None:
        self._debounce.stop()
        if self.slider.value() != self.c.profile.lighting.brightness:
            self.c.set_brightness(self.slider.value())
