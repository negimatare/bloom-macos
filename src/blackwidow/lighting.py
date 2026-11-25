"""High-level backlight control for the BlackWidow Lite."""

from __future__ import annotations

from enum import Enum

from . import protocol
from .device import Keyboard


class LightEffect(str, Enum):
    OFF = "off"
    STATIC = "static"
    BREATHING = "breathing"


# Effects not supported by OpenRazer for this model; testable via `bw experiment`.
EXPERIMENTAL = {
    "reactive": protocol.effect_reactive,
    "starlight": protocol.effect_starlight,
}


def percent_to_raw(percent: int) -> int:
    if not 0 <= percent <= 100:
        raise ValueError("brightness must be 0..100%")
    return round(percent * 255 / 100)


def raw_to_percent(raw: int) -> int:
    return round(raw * 100 / 255)


def get_brightness(kb: Keyboard) -> int:
    """Current brightness in percent."""
    response = kb.send(protocol.get_brightness())
    return raw_to_percent(response.arguments[2])


def set_brightness(kb: Keyboard, percent: int) -> None:
    kb.send(protocol.set_brightness(percent_to_raw(percent)))


def set_effect(kb: Keyboard, effect: LightEffect) -> None:
    builders = {
        LightEffect.OFF: protocol.effect_none,
        LightEffect.STATIC: protocol.effect_static,
        LightEffect.BREATHING: protocol.effect_breathing,
    }
    kb.send(builders[LightEffect(effect)]())
