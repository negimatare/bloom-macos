"""Key names <-> HID keyboard usage codes (USB HID usage page 0x07)."""

from __future__ import annotations

KEYBOARD_PAGE = 0x07

# name -> (usage id, label shown in the UI)
_KEYS: dict[str, tuple[int, str]] = {}


def _add(name: str, usage: int, label: str | None = None) -> None:
    _KEYS[name] = (usage, label or name.replace("_", " ").title())


for i, ch in enumerate("abcdefghijklmnopqrstuvwxyz"):
    _add(ch, 0x04 + i, ch.upper())
for i, ch in enumerate("1234567890"):
    _add(ch, 0x1E + i, ch)
for i in range(12):
    _add(f"f{i + 1}", 0x3A + i, f"F{i + 1}")
for i in range(12):
    _add(f"f{i + 13}", 0x68 + i, f"F{i + 13}")

for name, usage, label in [
    ("return", 0x28, "Return"),
    ("escape", 0x29, "Escape"),
    ("backspace", 0x2A, "Backspace"),
    ("tab", 0x2B, "Tab"),
    ("space", 0x2C, "Space"),
    ("minus", 0x2D, "- (Minus)"),
    ("equal", 0x2E, "= (Equal)"),
    ("left_bracket", 0x2F, "[ (Left Bracket)"),
    ("right_bracket", 0x30, "] (Right Bracket)"),
    ("backslash", 0x31, "\\ (Backslash)"),
    ("non_us_pound", 0x32, "Non-US # (ISO)"),
    ("semicolon", 0x33, "; (Semicolon)"),
    ("quote", 0x34, "' (Quote)"),
    ("grave", 0x35, "` (Grave)"),
    ("comma", 0x36, ", (Comma)"),
    ("period", 0x37, ". (Full Stop)"),
    ("slash", 0x38, "/ (Slash)"),
    ("caps_lock", 0x39, "Caps Lock"),
    ("print_screen", 0x46, "Print Screen"),
    ("scroll_lock", 0x47, "Scroll Lock"),
    ("pause", 0x48, "Pause"),
    ("insert", 0x49, "Insert"),
    ("home", 0x4A, "Home"),
    ("page_up", 0x4B, "Page Up"),
    ("delete", 0x4C, "Delete (Forward)"),
    ("end", 0x4D, "End"),
    ("page_down", 0x4E, "Page Down"),
    ("right", 0x4F, "Right Arrow"),
    ("left", 0x50, "Left Arrow"),
    ("down", 0x51, "Down Arrow"),
    ("up", 0x52, "Up Arrow"),
    ("non_us_backslash", 0x64, "Non-US \\ (ISO, next to Left Shift)"),
    ("application", 0x65, "Menu / Application"),
    ("left_control", 0xE0, "Left Control"),
    ("left_shift", 0xE1, "Left Shift"),
    ("left_option", 0xE2, "Left Option (Alt)"),
    ("left_command", 0xE3, "Left Command (Windows key)"),
    ("right_control", 0xE4, "Right Control"),
    ("right_shift", 0xE5, "Right Shift"),
    ("right_option", 0xE6, "Right Option (Alt Gr)"),
    ("right_command", 0xE7, "Right Command (Windows key)"),
]:
    _add(name, usage, label)

ALIASES = {
    "enter": "return",
    "esc": "escape",
    "caps": "caps_lock",
    "ctrl": "left_control",
    "control": "left_control",
    "shift": "left_shift",
    "alt": "left_option",
    "option": "left_option",
    "cmd": "left_command",
    "command": "left_command",
    "win": "left_command",
    "right_alt": "right_option",
    "right_cmd": "right_command",
    "right_ctrl": "right_control",
    "menu": "application",
}

_BY_USAGE = {usage: name for name, (usage, _) in _KEYS.items()}


def names() -> list[str]:
    return list(_KEYS)


def normalise(name: str) -> str:
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    key = ALIASES.get(key, key)
    if key not in _KEYS:
        raise KeyError(f"unknown key name: {name!r}")
    return key


def usage(name: str) -> int:
    return _KEYS[normalise(name)][0]


def label(name: str) -> str:
    return _KEYS[normalise(name)][1]


def name_for_usage(usage_id: int) -> str | None:
    return _BY_USAGE.get(usage_id)


def to_hidutil(name: str) -> int:
    """Full 64-bit value hidutil expects: (page << 32) | usage."""
    return (KEYBOARD_PAGE << 32) | usage(name)


def from_hidutil(value: int) -> str | None:
    if value >> 32 != KEYBOARD_PAGE:
        return None
    return name_for_usage(value & 0xFFFFFFFF)
