"""1:1 key remapping for the BlackWidow Lite only, via macOS's built-in hidutil.

Mappings are attached to the keyboard's HID services (matched by VID/PID), so
other keyboards are unaffected. macOS forgets them on reboot, and possibly
when the keyboard is unplugged, so they are re-applied from the saved config.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field

from . import hid_usages
from .device import PRODUCT_ID, VENDOR_ID

Mapping = tuple[str, str]  # (from key name, to key name)

MATCHING = json.dumps({"VendorID": VENDOR_ID, "ProductID": PRODUCT_ID})

_SRC = re.compile(r"HIDKeyboardModifierMappingSrc\s*=\s*(\d+)")
_DST = re.compile(r"HIDKeyboardModifierMappingDst\s*=\s*(\d+)")


class KeymapError(Exception):
    pass


def normalise(mappings: list[Mapping]) -> list[Mapping]:
    """Canonical key names; rejects unknown keys and duplicate sources."""
    result: list[Mapping] = []
    seen: set[str] = set()
    for src, dst in mappings:
        src_n, dst_n = hid_usages.normalise(src), hid_usages.normalise(dst)
        if src_n in seen:
            raise KeymapError(f"{src_n} is mapped more than once")
        seen.add(src_n)
        if src_n != dst_n:
            result.append((src_n, dst_n))
    return result


@dataclass(frozen=True)
class Change:
    mappings: list[Mapping]
    swapped_with: str | None = None  # the key that got the assigned key's old function
    duplicates: list[str] = field(default_factory=list)  # keys that already gave it, so no swap


def function_of(mappings: list[Mapping], key: str) -> str:
    """The function `key` gives now: its mapping, else its own."""
    return dict(mappings).get(key, key)


def _from_dict(functions: dict[str, str]) -> list[Mapping]:
    return normalise(list(functions.items()))


def remap(mappings: list[Mapping], key: str, function: str) -> list[Mapping]:
    """Make `key` give `function`, and change no other key."""
    functions = dict(mappings)
    functions[key] = function
    return _from_dict(functions)


def assign(mappings: list[Mapping], key: str, function: str, keys: list[str]) -> Change:
    """Make `key` give `function` without losing a function.

    The current functions decide, not the factory ones. When exactly one other
    physical key in `keys` gives `function`, it gets `key`'s current function.
    """
    old = function_of(mappings, key)
    holders = sorted(k for k in keys if k != key and function_of(mappings, k) == function)
    functions = dict(mappings)
    functions[key] = function
    if len(holders) != 1:
        return Change(_from_dict(functions), duplicates=holders if len(holders) > 1 else [])
    partner = holders[0]
    functions[partner] = old
    return Change(_from_dict(functions), swapped_with=partner)


def to_property(mappings: list[Mapping]) -> str:
    """JSON value for `hidutil property --set`."""
    entries = [
        {
            "HIDKeyboardModifierMappingSrc": hid_usages.to_hidutil(src),
            "HIDKeyboardModifierMappingDst": hid_usages.to_hidutil(dst),
        }
        for src, dst in normalise(mappings)
    ]
    return json.dumps({"UserKeyMapping": entries})


def parse_get_output(text: str) -> list[Mapping]:
    """Parse `hidutil property --get UserKeyMapping` output (first service)."""
    # Output lists one block per matched HID service; they all carry the same
    # mapping, so read the first block only.
    blocks = re.split(r"\n(?=[0-9a-f]+\s+UserKeyMapping)", text)
    for block in blocks:
        if "UserKeyMapping" not in block:
            continue
        mappings: list[Mapping] = []
        for entry in re.findall(r"\{[^}]*\}", block):
            src, dst = _SRC.search(entry), _DST.search(entry)
            if not (src and dst):
                continue
            src_n = hid_usages.from_hidutil(int(src.group(1)))
            dst_n = hid_usages.from_hidutil(int(dst.group(1)))
            if src_n and dst_n:
                mappings.append((src_n, dst_n))
        return mappings
    return []


def _hidutil(*args: str) -> str:
    try:
        result = subprocess.run(
            ["/usr/bin/hidutil", "property", "--matching", MATCHING, *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise KeymapError(f"hidutil failed: {exc}") from exc
    return result.stdout


def apply(mappings: list[Mapping]) -> None:
    """Replace the keyboard's mappings (an empty list clears them)."""
    _hidutil("--set", to_property(mappings))


def clear() -> None:
    apply([])


def current() -> list[Mapping]:
    return parse_get_output(_hidutil("--get", "UserKeyMapping"))
