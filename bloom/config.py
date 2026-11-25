"""Saved settings: profiles of lighting + key mappings, stored as JSON."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import keymap
from .lighting import LightEffect

APP_DIR = Path.home() / "Library" / "Application Support" / "Bloom"
CONFIG_PATH = Path(os.environ.get("BLOOM_CONFIG", APP_DIR / "config.json"))
DEFAULT_PROFILE = "Default"
PROFILE_ICONS = ("keyboard", "command", "code", "moon", "sun", "gamepad-2", "briefcase", "music")
DEFAULT_ICON = PROFILE_ICONS[0]
EXPORT_VERSION = 1


class ProfileError(ValueError):
    pass


def _mapping(item: object) -> tuple[str, str]:
    if not (isinstance(item, list) and len(item) == 2):
        raise ValueError(f"a mapping must be a pair of key names, not {item!r}")
    return str(item[0]), str(item[1])


@dataclass
class Lighting:
    effect: str = LightEffect.STATIC.value
    brightness: int = 100  # percent


@dataclass
class Profile:
    lighting: Lighting = field(default_factory=Lighting)
    mappings: list[tuple[str, str]] = field(default_factory=list)
    icon: str = DEFAULT_ICON

    @classmethod
    def from_dict(cls, data: dict) -> Profile:
        lighting = Lighting(**data.get("lighting", {}))
        LightEffect(lighting.effect)  # validate
        if type(lighting.brightness) is not int or not 0 <= lighting.brightness <= 100:
            raise ValueError(f"brightness must be a whole number from 0 to 100, not {lighting.brightness!r}")
        mappings = [_mapping(m) for m in data.get("mappings", [])]
        icon = data.get("icon", DEFAULT_ICON)
        return cls(lighting=lighting, mappings=mappings,
                   icon=icon if icon in PROFILE_ICONS else DEFAULT_ICON)

    def copy(self) -> Profile:
        return Profile.from_dict(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "icon": self.icon,
            "lighting": asdict(self.lighting),
            "mappings": [list(m) for m in self.mappings],
        }


@dataclass
class Config:
    active_profile: str = DEFAULT_PROFILE
    profiles: dict[str, Profile] = field(
        default_factory=lambda: {DEFAULT_PROFILE: Profile()}
    )

    @property
    def active(self) -> Profile:
        return self.profiles[self.active_profile]

    @classmethod
    def from_dict(cls, data: dict) -> Config:
        profiles = {
            name: Profile.from_dict(p) for name, p in data.get("profiles", {}).items()
        } or {DEFAULT_PROFILE: Profile()}
        active = data.get("active_profile", DEFAULT_PROFILE)
        if active not in profiles:
            active = next(iter(profiles))
        return cls(active_profile=active, profiles=profiles)

    # ---- profile rules ------------------------------------------------------

    def free_name(self, base: str) -> str:
        """`base`, or `base 2`, `base 3`… when a profile already has the name."""
        name, n = base, 1
        while name in self.profiles:
            n += 1
            name = f"{base} {n}"
        return name

    def _new_name(self, name: str) -> str:
        name = name.strip()
        if not name:
            raise ProfileError("A profile needs a name.")
        if name in self.profiles:
            raise ProfileError(f"A profile called '{name}' already exists.")
        return name

    def create(self, name: str, copy_of: str | None = None) -> str:
        name = self._new_name(name)
        self.profiles[name] = self.profiles[copy_of].copy() if copy_of else Profile()
        return name

    def rename(self, old: str, new: str) -> str:
        if new.strip() == old:
            return old
        new = self._new_name(new)
        self.profiles = {(new if k == old else k): v for k, v in self.profiles.items()}
        if self.active_profile == old:
            self.active_profile = new
        return new

    def delete(self, name: str) -> None:
        if len(self.profiles) <= 1:
            raise ProfileError("You need at least one profile.")
        del self.profiles[name]
        if self.active_profile == name:
            self.active_profile = next(iter(self.profiles))

    def restore_default(self, name: str) -> None:
        """No remaps and factory lighting; the name and icon stay."""
        profile = self.profiles[name]
        profile.lighting, profile.mappings = Lighting(), []

    def export_profile(self, name: str) -> str:
        data = {"bloom_profile": EXPORT_VERSION, "name": name, **self.profiles[name].to_dict()}
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    def import_profile(self, text: str) -> str:
        """Add the exported profile in `text`; the whole file is checked first."""
        try:
            data = json.loads(text)
            if data.get("bloom_profile") != EXPORT_VERSION:
                raise ValueError("it is not a Bloom profile")
            profile = Profile.from_dict(data)
            profile.mappings = keymap.normalise(profile.mappings)
            base = str(data.get("name") or "Imported").strip() or "Imported"
        except (ValueError, TypeError, KeyError, AttributeError, keymap.KeymapError) as exc:
            raise ProfileError(f"This file can't be imported: {exc}") from exc
        name = self.free_name(base)
        self.profiles[name] = profile
        return name

    def to_dict(self) -> dict:
        return {
            "active_profile": self.active_profile,
            "profiles": {name: p.to_dict() for name, p in self.profiles.items()},
        }


def load(path: Path = CONFIG_PATH) -> Config:
    try:
        return Config.from_dict(json.loads(path.read_text()))
    except FileNotFoundError:
        return Config()


def save(config: Config, path: Path = CONFIG_PATH) -> None:
    """Write atomically, so the watcher never reads a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".config-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(config.to_dict(), f, indent=2)
        f.write("\n")
    os.replace(tmp, path)
