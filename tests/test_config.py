import json

import pytest

from bloom import config


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


def test_restore_default_clears_remaps_and_lighting_but_keeps_the_icon():
    cfg = config.Config()
    cfg.active.icon = "moon"
    cfg.active.lighting.brightness = 35
    cfg.active.mappings = [("caps_lock", "escape")]
    cfg.restore_default("Default")
    assert cfg.active.mappings == []
    assert cfg.active.lighting == config.Lighting()
    assert cfg.active.icon == "moon"


def test_rename_to_a_used_name_is_refused():
    cfg = config.Config()
    cfg.create("Work")
    with pytest.raises(config.ProfileError):
        cfg.rename("Work", "Default")


def test_the_last_profile_cannot_be_deleted():
    cfg = config.Config()
    with pytest.raises(config.ProfileError):
        cfg.delete("Default")


def test_export_then_import_adds_a_copy_with_a_free_name():
    cfg = config.Config()
    cfg.active.icon = "command"
    cfg.active.lighting.brightness = 35
    cfg.active.mappings = [("left_option", "left_command")]
    name = cfg.import_profile(cfg.export_profile("Default"))
    assert name == "Default 2"
    assert cfg.profiles[name].to_dict() == cfg.active.to_dict()


@pytest.mark.parametrize("text", [
    '{"bloom_profile": 1, "name": "X", "mappings": [["caps_lock", "hyper"]]}',
    '{"bloom_profile": 1, "name": "X", "lighting": {"colour": "pink"}}',
    '{"bloom_profile": 1, "name": "X", "lighting": {"brightness": "loud"}}',
    '{"bloom_profile": 1, "name": "X", "lighting": {"brightness": 101}}',
    '{"bloom_profile": 1, "name": "X", "mappings": ["ab"]}',
    "not json",
])
def test_a_bad_import_file_raises_one_error_and_changes_nothing(text):
    cfg = config.Config()
    before = cfg.to_dict()
    with pytest.raises(config.ProfileError):
        cfg.import_profile(text)
    assert cfg.to_dict() == before


def test_a_file_without_icons_still_loads(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"profiles": {"A": {"mappings": [["a", "b"]]}}}))
    assert config.load(path).profiles["A"].icon == config.DEFAULT_ICON
