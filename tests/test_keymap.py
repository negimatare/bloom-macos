import json

import pytest

from bloom import hid_usages, keymap, layout

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


KEYS = layout.KEY_NAMES


def as_dict(change):
    return dict(change.mappings)


def test_assign_swaps_with_the_one_key_that_gives_the_function():
    change = keymap.assign([], "left_option", "left_command", KEYS)
    assert as_dict(change) == {"left_option": "left_command", "left_command": "left_option"}
    assert change.swapped_with == "left_command"


def test_assign_is_a_plain_remap_when_no_key_gives_the_function():
    change = keymap.assign([], "caps_lock", "f13", KEYS)
    assert change.mappings == [("caps_lock", "f13")]
    assert change.swapped_with is None


def test_assign_does_not_swap_when_several_keys_give_the_function():
    mappings = [("a", "left_command")]
    change = keymap.assign(mappings, "left_option", "left_command", KEYS)
    assert as_dict(change) == {"a": "left_command", "left_option": "left_command"}
    assert change.swapped_with is None
    assert change.duplicates == ["a", "left_command"]


def test_assign_uses_current_assignments_so_no_function_is_lost():
    first = keymap.assign([], "left_option", "left_command", KEYS)
    second = keymap.assign(first.mappings, "left_option", "left_control", KEYS)
    assert as_dict(second) == {
        "left_option": "left_control",
        "left_command": "left_option",
        "left_control": "left_command",
    }
    assert second.swapped_with == "left_control"


def test_revert_by_assign_restores_both_swapped_keys():
    swapped = keymap.assign([], "left_option", "left_command", KEYS)
    reverted = keymap.assign(swapped.mappings, "left_option", "left_option", KEYS)
    assert reverted.mappings == []
    assert reverted.swapped_with == "left_command"


def test_remap_keeps_both_keys_on_the_same_function():
    assert keymap.remap([("caps_lock", "f13")], "caps_lock", "escape") == [("caps_lock", "escape")]


def test_every_key_has_a_short_label_that_fits_on_a_keycap():
    assert hid_usages.short_label("left_command") == "⌘"
    assert all(len(hid_usages.short_label(n)) <= 5 for n in hid_usages.names())
