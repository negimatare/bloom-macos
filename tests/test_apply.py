import pytest

from bloom import apply, device, keymap
from bloom.config import Profile


def test_a_lighting_failure_still_applies_the_remaps(monkeypatch):
    applied = []
    monkeypatch.setattr(keymap, "apply", applied.append)

    def no_keyboard(_profile):
        raise device.DeviceError("Input Monitoring is off")

    monkeypatch.setattr(apply, "apply_lighting", no_keyboard)
    with pytest.raises(device.DeviceError):
        apply.apply_profile(Profile(mappings=[("caps_lock", "escape")]))
    assert applied == [[("caps_lock", "escape")]]
