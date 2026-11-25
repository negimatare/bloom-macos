"""Razer 90-byte control report: building, checksumming and parsing.

Layout and command values reimplemented from the publicly documented
OpenRazer protocol (driver/razercommon.h, driver/razerchromacommon.c):

    byte  0      status
    byte  1      transaction id
    bytes 2-3    remaining packets (big endian)
    byte  4      protocol type (always 0x00)
    byte  5      data size (number of meaningful argument bytes)
    byte  6      command class
    byte  7      command id (high bit set = "get" request)
    bytes 8-87   arguments (80 bytes)
    byte  88     CRC: XOR of bytes 2..87
    byte  89     reserved
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

REPORT_LEN = 90
ARGS_LEN = 80

# BlackWidow Lite uses transaction id 0x3F for all lighting commands.
TRANSACTION_ID = 0x3F

# Storage / LED identifiers
NOSTORE = 0x00
VARSTORE = 0x01  # persist the setting on the keyboard
BACKLIGHT_LED = 0x05

# Command classes / ids
CLASS_EXTENDED_MATRIX = 0x0F
CMD_SET_EFFECT = 0x02
CMD_SET_BRIGHTNESS = 0x04
CMD_GET_BRIGHTNESS = 0x84


class Status(IntEnum):
    NEW = 0x00
    BUSY = 0x01
    SUCCESS = 0x02
    FAILURE = 0x03
    TIMEOUT = 0x04
    NOT_SUPPORTED = 0x05


class Effect(IntEnum):
    """Extended-matrix effect ids."""

    NONE = 0x00
    STATIC = 0x01
    BREATHING = 0x02
    REACTIVE = 0x05  # experimental on the BlackWidow Lite
    STARLIGHT = 0x07  # experimental on the BlackWidow Lite


WHITE = (0xFF, 0xFF, 0xFF)


def crc(raw: bytes | bytearray) -> int:
    """XOR of bytes 2..87 of a 90-byte report."""
    value = 0
    for b in raw[2:88]:
        value ^= b
    return value


@dataclass
class Report:
    command_class: int
    command_id: int
    data_size: int
    arguments: bytearray = field(default_factory=lambda: bytearray(ARGS_LEN))
    status: int = Status.NEW
    transaction_id: int = TRANSACTION_ID
    remaining_packets: int = 0
    protocol_type: int = 0x00

    def to_bytes(self) -> bytes:
        if len(self.arguments) != ARGS_LEN:
            raise ValueError(f"arguments must be {ARGS_LEN} bytes")
        raw = bytearray(REPORT_LEN)
        raw[0] = self.status
        raw[1] = self.transaction_id
        raw[2:4] = self.remaining_packets.to_bytes(2, "big")
        raw[4] = self.protocol_type
        raw[5] = self.data_size
        raw[6] = self.command_class
        raw[7] = self.command_id
        raw[8:88] = self.arguments
        raw[88] = crc(raw)
        raw[89] = 0x00
        return bytes(raw)

    @classmethod
    def from_bytes(cls, raw: bytes | bytearray) -> Report:
        if len(raw) != REPORT_LEN:
            raise ValueError(f"expected {REPORT_LEN} bytes, got {len(raw)}")
        return cls(
            status=raw[0],
            transaction_id=raw[1],
            remaining_packets=int.from_bytes(raw[2:4], "big"),
            protocol_type=raw[4],
            data_size=raw[5],
            command_class=raw[6],
            command_id=raw[7],
            arguments=bytearray(raw[8:88]),
        )

    def matches(self, request: Report) -> bool:
        """True if this response answers the given request."""
        return (
            self.command_class == request.command_class
            and self.command_id == request.command_id
        )


def _effect(effect: Effect, size: int) -> Report:
    report = Report(CLASS_EXTENDED_MATRIX, CMD_SET_EFFECT, size)
    report.arguments[0] = VARSTORE
    report.arguments[1] = BACKLIGHT_LED
    report.arguments[2] = effect
    return report


def effect_none() -> Report:
    return _effect(Effect.NONE, 0x06)


def effect_static(rgb: tuple[int, int, int] = WHITE) -> Report:
    report = _effect(Effect.STATIC, 0x09)
    report.arguments[5] = 0x01
    report.arguments[6:9] = bytes(rgb)
    return report


def effect_breathing(rgb: tuple[int, int, int] = WHITE) -> Report:
    report = _effect(Effect.BREATHING, 0x09)
    report.arguments[3] = 0x01  # single colour
    report.arguments[5] = 0x01
    report.arguments[6:9] = bytes(rgb)
    return report


def effect_reactive(speed: int = 2, rgb: tuple[int, int, int] = WHITE) -> Report:
    report = _effect(Effect.REACTIVE, 0x09)
    report.arguments[4] = max(1, min(4, speed))
    report.arguments[5] = 0x01
    report.arguments[6:9] = bytes(rgb)
    return report


def effect_starlight(speed: int = 2, rgb: tuple[int, int, int] = WHITE) -> Report:
    report = _effect(Effect.STARLIGHT, 0x09)
    report.arguments[4] = max(1, min(3, speed))
    report.arguments[5] = 0x01
    report.arguments[6:9] = bytes(rgb)
    return report


def set_brightness(value: int) -> Report:
    """value: 0..255"""
    if not 0 <= value <= 255:
        raise ValueError("brightness must be 0..255")
    report = Report(CLASS_EXTENDED_MATRIX, CMD_SET_BRIGHTNESS, 0x03)
    report.arguments[0] = VARSTORE
    report.arguments[1] = BACKLIGHT_LED
    report.arguments[2] = value
    return report


def get_brightness() -> Report:
    report = Report(CLASS_EXTENDED_MATRIX, CMD_GET_BRIGHTNESS, 0x03)
    report.arguments[0] = VARSTORE
    report.arguments[1] = BACKLIGHT_LED
    return report
