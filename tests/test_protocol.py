"""Report encoding checks. Expected bytes are derived by hand from the
OpenRazer helpers (razerchromacommon.c) for the BlackWidow Lite."""

import pytest

from blackwidow import protocol
from blackwidow.protocol import REPORT_LEN, Report


def header(raw: bytes) -> list[int]:
    return list(raw[:8])


def args(raw: bytes, n: int) -> list[int]:
    return list(raw[8 : 8 + n])


def test_report_length_and_trailer():
    raw = protocol.get_brightness().to_bytes()
    assert len(raw) == REPORT_LEN
    assert raw[89] == 0x00
    assert all(b == 0 for b in raw[8 + 2 : 88])


def test_crc_is_xor_of_bytes_2_to_87():
    raw = protocol.set_brightness(128).to_bytes()
    expected = 0
    for b in raw[2:88]:
        expected ^= b
    assert raw[88] == expected


def test_get_brightness():
    raw = protocol.get_brightness().to_bytes()
    assert header(raw) == [0x00, 0x3F, 0x00, 0x00, 0x00, 0x03, 0x0F, 0x84]
    assert args(raw, 3) == [0x01, 0x05, 0x00]
    assert raw[88] == 0x8C


def test_set_brightness():
    raw = protocol.set_brightness(255).to_bytes()
    assert header(raw) == [0x00, 0x3F, 0x00, 0x00, 0x00, 0x03, 0x0F, 0x04]
    assert args(raw, 3) == [0x01, 0x05, 0xFF]
    assert raw[88] == 0xF3


@pytest.mark.parametrize("value", [-1, 256])
def test_set_brightness_range(value):
    with pytest.raises(ValueError):
        protocol.set_brightness(value)


def test_effect_none():
    raw = protocol.effect_none().to_bytes()
    assert header(raw)[5:] == [0x06, 0x0F, 0x02]
    assert args(raw, 6) == [0x01, 0x05, 0x00, 0x00, 0x00, 0x00]


def test_effect_static_white():
    raw = protocol.effect_static().to_bytes()
    assert header(raw)[5:] == [0x09, 0x0F, 0x02]
    assert args(raw, 9) == [0x01, 0x05, 0x01, 0x00, 0x00, 0x01, 0xFF, 0xFF, 0xFF]
    assert raw[88] == 0xFF


def test_effect_breathing_single():
    raw = protocol.effect_breathing().to_bytes()
    assert args(raw, 9) == [0x01, 0x05, 0x02, 0x01, 0x00, 0x01, 0xFF, 0xFF, 0xFF]


def test_effect_reactive_clamps_speed():
    raw = protocol.effect_reactive(speed=9).to_bytes()
    assert args(raw, 9) == [0x01, 0x05, 0x05, 0x00, 0x04, 0x01, 0xFF, 0xFF, 0xFF]


def test_effect_starlight_clamps_speed():
    raw = protocol.effect_starlight(speed=0).to_bytes()
    assert args(raw, 9) == [0x01, 0x05, 0x07, 0x00, 0x01, 0x01, 0xFF, 0xFF, 0xFF]


def test_round_trip():
    original = protocol.effect_static()
    parsed = Report.from_bytes(original.to_bytes())
    assert parsed.to_bytes() == original.to_bytes()
    assert parsed.matches(original)
