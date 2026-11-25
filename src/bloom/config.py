"""Saved settings: profiles of lighting + key mappings, stored as JSON."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .lighting import LightEffect

APP_DIR = Path.home() / "Library" / "Application Support" / "Bloom"
CONFIG_PATH = Path(os.environ.get("BLOOM_CONFIG", APP_DIR / "config.json"))
DEFAULT_PROFILE = "Default"


@dataclass
class Lighting:
    effect: str = LightEffect.STATIC.value
    brightness: int = 100  # percent


@dataclass
class Profile:
    lighting: Lighting = field(default_factory=Lighting)
    mappings: list[tuple[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Profile:
        lighting = Lighting(**data.get("lighting", {}))
        LightEffect(lighting.effect)  # validate
        mappings = [(str(a), str(b)) for a, b in data.get("mappings", [])]
        return cls(lighting=lighting, mappings=mappings)

    def to_dict(self) -> dict:
        return {
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
