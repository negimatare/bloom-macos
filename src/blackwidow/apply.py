"""Push a saved profile to the keyboard (lighting) and macOS (mappings)."""

from __future__ import annotations

from . import keymap, lighting
from .config import Profile
from .device import Keyboard
from .lighting import LightEffect


def apply_lighting(profile: Profile, kb: Keyboard | None = None) -> None:
    own = kb is None
    kb = kb or Keyboard()
    try:
        effect = LightEffect(profile.lighting.effect)
        lighting.set_effect(kb, effect)
        if effect is not LightEffect.OFF:
            lighting.set_brightness(kb, profile.lighting.brightness)
    finally:
        if own:
            kb.close()


def apply_mappings(profile: Profile) -> None:
    keymap.apply(profile.mappings)


def apply_profile(profile: Profile) -> None:
    apply_lighting(profile)
    apply_mappings(profile)
