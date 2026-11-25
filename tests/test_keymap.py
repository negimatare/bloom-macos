import json

import pytest

from blackwidow import hid_usages, keymap

SAMPLE_GET = """RegistryID  Key                   Value
10000191f   UserKeyMapping   (
        {
        HIDKeyboardModifierMappingDst = 30064771113;
        HIDKeyboardModifierMappingSrc = 30064771129;
    },
        {
        HIDKeyboardModifierMappingDst = 30064771298;
        HIDKeyboardModifierMappingSrc = 30064771299;
    }
)
100001918   UserKeyMapping   (
        {
        HIDKeyboardModifierMappingDst = 30064771113;
        HIDKeyboardModifierMappingSrc = 30064771129;
    }
)
"""


def test_hidutil_values():
    assert hid_usages.to_hidutil("caps_lock") == 0x700000039 == 30064771129
    assert hid_usages.to_hidutil("escape") == 0x700000029 == 30064771113
    assert hid_usages.from_hidutil(30064771129) == "caps_lock"
    assert hid_usages.from_hidutil(0x0C000000E9) is None  # consumer page


def test_aliases_and_unknown_names():
    assert hid_usages.normalise("Caps Lock") == "caps_lock"
    assert hid_usages.normalise("esc") == "escape"
    assert hid_usages.normalise("cmd") == "left_command"
    with pytest.raises(KeyError):
        hid_usages.normalise("hyper")


def test_names_unique_usages():
    usages = [hid_usages.usage(n) for n in hid_usages.names()]
    assert len(usages) == len(set(usages))


def test_to_property():
    value = json.loads(keymap.to_property([("caps", "esc")]))
    assert value == {
        "UserKeyMapping": [
            {
                "HIDKeyboardModifierMappingSrc": 30064771129,
                "HIDKeyboardModifierMappingDst": 30064771113,
            }
        ]
    }


def test_to_property_empty_clears():
    assert json.loads(keymap.to_property([])) == {"UserKeyMapping": []}


def test_identity_mappings_dropped_and_duplicates_rejected():
    assert keymap.normalise([("a", "a"), ("b", "c")]) == [("b", "c")]
    with pytest.raises(keymap.KeymapError):
        keymap.normalise([("a", "b"), ("a", "c")])


def test_parse_get_output_reads_first_service():
    assert keymap.parse_get_output(SAMPLE_GET) == [
        ("caps_lock", "escape"),
        ("left_command", "left_option"),
    ]


def test_parse_get_output_null():
    text = "RegistryID  Key                   Value\n10000191f   UserKeyMapping   (null)\n"
    assert keymap.parse_get_output(text) == []
