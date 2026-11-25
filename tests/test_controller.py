from types import SimpleNamespace

import pytest

from bloom import config, device, keymap, watcher
from bloom.gui import controller as controller_module
from bloom.gui.controller import Controller


@pytest.fixture
def fake(monkeypatch, qt_app):
    """A Controller on fakes: `plugged` connects the keyboard, `calls` records what reaches it."""
    world = SimpleNamespace(plugged=True, calls=[], errors=[], save_fails=False)

    def save(_cfg):
        if world.save_fails:
            raise OSError("disk full")

    monkeypatch.setattr(config, "load", config.Config)
    monkeypatch.setattr(config, "save", save)
    monkeypatch.setattr(device, "list_interfaces",
                        lambda: [SimpleNamespace(path=b"razer")] if world.plugged else [])
    monkeypatch.setattr(device, "input_monitoring_status", lambda: "granted")
    monkeypatch.setattr(watcher, "agent_status", lambda: "not installed")
    monkeypatch.setattr(keymap, "clear", lambda: world.calls.append(("clear",)))
    monkeypatch.setattr(controller_module, "apply_mappings",
                        lambda p: world.calls.append(("mappings", list(p.mappings))))
    monkeypatch.setattr(controller_module, "apply_lighting",
                        lambda p: world.calls.append(("lighting", p.lighting.brightness)))
    monkeypatch.setattr(controller_module, "apply_profile", lambda p: world.calls.append(
        ("profile", list(p.mappings), p.lighting.brightness)))

    def start() -> Controller:
        c = Controller()
        c.error.connect(world.errors.append)
        world.calls.clear()
        return c

    world.start = start
    return world


def test_undo_after_restore_to_default_brings_back_remaps_and_lighting(fake):
    c = fake.start()
    c.profile.mappings = [("left_option", "left_command")]
    c.profile.lighting.brightness = 35
    c.restore_default("Default")
    assert c.undo()
    assert c.profile.mappings == [("left_option", "left_command")]
    assert c.profile.lighting.brightness == 35
    assert fake.calls[-1] == ("profile", [("left_option", "left_command")], 35)


def test_undo_of_a_remap_keeps_a_later_lighting_change(fake):
    fake.plugged = False
    c = fake.start()
    c.assign("caps_lock", "escape")
    c.set_brightness(20)
    assert c.undo()
    assert c.profile.mappings == []
    assert c.profile.lighting.brightness == 20


def test_deleting_the_active_profile_applies_another_and_undo_makes_it_active_again(fake):
    c = fake.start()
    c.config.create("Work")
    c.config.profiles["Work"].mappings = [("a", "b")]
    c.config.active_profile = "Work"
    assert c.delete_profile("Work")
    assert c.config.active_profile == "Default"
    assert fake.calls[-1] == ("profile", [], 100)
    assert c.undo()
    assert c.config.active_profile == "Work"
    assert fake.calls[-1] == ("profile", [("a", "b")], 100)


def test_keep_both_gives_the_swapped_key_its_function_back(fake):
    c = fake.start()
    c.assign("caps_lock", "escape")
    assert c.keep_both()
    assert c.profile.mappings == [("caps_lock", "escape")]
    assert fake.calls[-1] == ("mappings", [("caps_lock", "escape")])


def test_listening_clears_the_remaps_and_stopping_applies_them_again(fake):
    c = fake.start()
    c.profile.mappings = [("caps_lock", "escape")]
    c.start_listening()
    assert fake.calls == [("clear",)]
    c.stop_listening()
    assert fake.calls[-1] == ("mappings", [("caps_lock", "escape")])


def test_edit_renames_the_profile_and_sets_its_icon(fake):
    c = fake.start()
    assert c.edit_profile("Default", "Evening", "moon") == "Evening"
    assert c.config.profiles["Evening"].icon == "moon"


def test_a_remap_that_does_not_reach_the_keyboard_reports_only_the_error(fake, monkeypatch):
    def hidutil_fails(_profile):
        raise keymap.KeymapError("hidutil failed")

    monkeypatch.setattr(controller_module, "apply_mappings", hidutil_fails)
    c = fake.start()
    assert c.assign("caps_lock", "escape") is None
    assert fake.errors == ["hidutil failed"]


def test_a_failed_save_still_applies_the_remaps_and_reports_the_error(fake):
    c = fake.start()
    fake.save_fails = True
    assert c.assign("caps_lock", "escape") is None
    assert fake.calls[-1][0] == "mappings"
    assert fake.errors == ["The settings can't be saved: disk full"]


def test_a_keyboard_that_connects_gets_the_lighting_changed_while_unplugged(fake):
    fake.plugged = False
    c = fake.start()
    c.set_brightness(20)
    fake.plugged = True
    c._poll()
    assert ("lighting", 20) in fake.calls
