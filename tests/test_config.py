import json

import pytest

from blackwidow import config


def test_missing_file_gives_default(tmp_path):
    cfg = config.load(tmp_path / "none.json")
    assert cfg.active_profile == "Default"
    assert cfg.active.mappings == []


def test_round_trip(tmp_path):
    path = tmp_path / "c.json"
    cfg = config.Config()
    cfg.active.lighting.brightness = 40
    cfg.active.mappings = [("caps_lock", "escape")]
    cfg.profiles["Work"] = config.Profile(mappings=[("a", "b")])
    config.save(cfg, path)
    loaded = config.load(path)
    assert loaded.to_dict() == cfg.to_dict()
    assert json.loads(path.read_text())["profiles"]["Default"]["mappings"] == [["caps_lock", "escape"]]


def test_unknown_active_profile_falls_back(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"active_profile": "Gone", "profiles": {"A": {}}}))
    assert config.load(path).active_profile == "A"


def test_invalid_effect_rejected(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"profiles": {"A": {"lighting": {"effect": "rainbow"}}}}))
    with pytest.raises(ValueError):
        config.load(path)
