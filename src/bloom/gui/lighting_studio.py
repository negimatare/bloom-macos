"""Lighting Studio: backlight switch, live brightness, presets and effect."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget

from ..lighting import LightEffect
from . import icons, theme
from .backlight_preview import KeyboardPreview
from .controller import Controller
from .widgets import StatusLine, ToggleSwitch, card, label, segmented, separator, text_block

DEBOUNCE_MS = 150
PRESETS = [("Night", 15), ("Soft", 35), ("Normal", 70), ("Maximum", 100)]
EFFECTS = [LightEffect.STATIC, LightEffect.BREATHING]


class LightingStudio(QWidget):
    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self.c = controller

        self.state = label(role="muted")
        header = QHBoxLayout()
        header.addLayout(text_block("Lighting", "Personalise the backlight of your keyboard.", "title"), 1)
        header.addWidget(self.state, alignment=Qt.AlignTop)

        self.preview = KeyboardPreview()
        preview_card = card()
        QVBoxLayout(preview_card).addWidget(self.preview)

        self.switch = ToggleSwitch("Backlight")
        backlight_row = QHBoxLayout()
        backlight_row.addLayout(text_block("Backlight", "White LEDs · one zone"), 1)
        backlight_row.addWidget(self.switch)

        self.value = label(role="value")
        brightness_row = QHBoxLayout()
        brightness_row.addWidget(label("Brightness", "heading"), 1)
        brightness_row.addWidget(self.value)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setAccessibleName("Brightness")
        slider_row = QHBoxLayout()
        dim, bright = QLabel(), QLabel()
        dim.setPixmap(icons.pixmap("sun-dim", theme.MUTED))
        bright.setPixmap(icons.pixmap("sun", theme.MUTED))
        slider_row.addWidget(dim)
        slider_row.addWidget(self.slider, 1)
        slider_row.addWidget(bright)

        presets_row = QHBoxLayout()
        self.presets: list[tuple[QPushButton, int]] = []
        for name, percent in PRESETS:
            button = QPushButton(f"{name}\n{percent}%")
            button.setCheckable(True)
            button.setProperty("role", "preset")
            button.setCursor(Qt.PointingHandCursor)
            button.setAccessibleName(f"{name}, {percent}% brightness")
            button.clicked.connect(lambda _=False, p=percent: self._on_preset(p))
            presets_row.addWidget(button)
            self.presets.append((button, percent))

        effect_buttons, self.effects = segmented(["Static", "Breathing"], "segment")
        effect_row = QHBoxLayout()
        effect_row.addLayout(text_block("Effect", "Breathing fades the light slowly in and out."), 1)
        effect_row.addLayout(effect_buttons)

        settings = card()
        settings_layout = QVBoxLayout(settings)
        settings_layout.setContentsMargins(18, 16, 18, 16)
        settings_layout.setSpacing(12)
        settings_layout.addLayout(backlight_row)
        settings_layout.addWidget(separator())
        settings_layout.addLayout(brightness_row)
        settings_layout.addLayout(slider_row)
        settings_layout.addLayout(presets_row)
        settings_layout.addWidget(separator())
        settings_layout.addLayout(effect_row)

        self.status = StatusLine()

        page = QVBoxLayout(self)
        page.setContentsMargins(24, 20, 24, 16)
        page.setSpacing(14)
        page.addLayout(header)
        page.addWidget(preview_card)
        page.addWidget(settings)
        page.addStretch(1)
        page.addWidget(self.status)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(DEBOUNCE_MS)
        self._debounce.timeout.connect(self._commit_brightness)

        self.switch.toggled.connect(self._on_switch)
        self.slider.valueChanged.connect(self._on_slider)
        self.slider.sliderReleased.connect(self._commit_brightness)
        self.effects.idClicked.connect(self._on_effect)
        self.c.config_changed.connect(self.refresh)
        self.c.connection_changed.connect(self._show_footer)
        self.refresh()

    # ---- state -> widgets ----------------------------------------------------

    def refresh(self) -> None:
        light = self.c.profile.lighting
        effect = LightEffect(light.effect)
        lit = effect is not LightEffect.OFF
        for w in (self.switch, self.slider):
            w.blockSignals(True)
        self.switch.setChecked(lit)
        if not self._debounce.isActive():
            self.slider.setValue(light.brightness)
        if lit:
            self.effects.button(EFFECTS.index(effect)).setChecked(True)
        elif self.effects.checkedButton() is None:
            self.effects.button(0).setChecked(True)  # what switching on restores
        for w in (self.switch, self.slider):
            w.blockSignals(False)
        for w in (self.slider, *self.effects.buttons(), *(b for b, _ in self.presets)):
            w.setEnabled(lit)
        self.state.setText("● On" if lit else "○ Off")
        self.state.setStyleSheet(f"color: {theme.ACCENT if lit else theme.MUTED};")
        self._show_value(self.slider.value())
        self._show_footer()

    def _show_value(self, value: int) -> None:
        self.value.setText(f"{value}%")
        for button, percent in self.presets:
            button.setChecked(percent == value)
        self.preview.set_state(self._current_effect(), value)

    def _show_footer(self, *_args) -> None:
        profile = self.c.config.active_profile
        if self.c.connected:
            self.status.show_status(f"Applied to the keyboard · profile {profile}", ok=True)
        else:
            self.status.show_status(
                f"Saved to profile {profile}. It applies when the keyboard connects.", ok=False)

    # ---- widgets -> keyboard -------------------------------------------------

    def _selected_effect(self) -> LightEffect:
        return EFFECTS[max(self.effects.checkedId(), 0)]

    def _current_effect(self) -> LightEffect:
        return self._selected_effect() if self.switch.isChecked() else LightEffect.OFF

    def _on_switch(self, on: bool) -> None:
        self.c.set_effect(self._selected_effect() if on else LightEffect.OFF)

    def _on_effect(self, index: int) -> None:
        if self.switch.isChecked():
            self.c.set_effect(EFFECTS[index])

    def _on_preset(self, percent: int) -> None:
        self.slider.setValue(percent)
        self._commit_brightness()

    def _on_slider(self, value: int) -> None:
        self._show_value(value)
        self._debounce.start()

    def _commit_brightness(self) -> None:
        self._debounce.stop()
        if self.slider.value() != self.c.profile.lighting.brightness:
            self.c.set_brightness(self.slider.value())
        else:
            self._show_value(self.slider.value())
