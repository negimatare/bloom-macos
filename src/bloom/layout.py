"""Physical layout of the Razer BlackWidow Lite (ANSI, tenkeyless).

Positions and widths are in key units (1 = one letter key), on the usual
tenkeyless grid: a 0.25-unit gap under the function row and before the
navigation cluster.
"""

from __future__ import annotations

from dataclasses import dataclass

GAP = 0.25
NAV_X = 15 + GAP


@dataclass(frozen=True)
class Key:
    name: str | None  # None: handled by the keyboard firmware, macOS never sees it
    legend: str  # what is printed on the Razer keycap
    x: float
    y: float
    width: float = 1.0

    @property
    def title(self) -> str:
        """How messages name the key, for example "Left Alt" or "Caps Lock"."""
        side, _, kind = (self.name or "").partition("_")
        if side in ("left", "right") and kind in _SIDED_KINDS:
            return f"{side.title()} {self.legend}"
        return _TITLES.get(self.legend, self.legend)


_SIDED_KINDS = {"control", "shift", "option", "command"}
_TITLES = {"Caps": "Caps Lock", "Esc": "Escape", "Del": "Delete", "Ins": "Insert",
           "PgUp": "Page Up", "PgDn": "Page Down", "PrtSc": "Print Screen",
           "ScrLk": "Scroll Lock", "↑": "Up", "↓": "Down", "←": "Left", "→": "Right"}


# Each row: (key name, legend, width); a None name with a "" legend is a gap.
_Row = list[tuple[str | None, str, float]]

_FUNCTION_ROW: _Row = [
    ("escape", "Esc", 1), (None, "", 1),
    *[(f"f{i}", f"F{i}", 1) for i in range(1, 5)], (None, "", 0.5),
    *[(f"f{i}", f"F{i}", 1) for i in range(5, 9)], (None, "", 0.5),
    *[(f"f{i}", f"F{i}", 1) for i in range(9, 13)],
]

_MAIN_ROWS: list[_Row] = [
    [("grave", "`", 1), *[(d, d, 1) for d in "1234567890"],
     ("minus", "-", 1), ("equal", "=", 1), ("backspace", "Backspace", 2)],
    [("tab", "Tab", 1.5), *[(c, c.upper(), 1) for c in "qwertyuiop"],
     ("left_bracket", "[", 1), ("right_bracket", "]", 1), ("backslash", "\\", 1.5)],
    [("caps_lock", "Caps", 1.75), *[(c, c.upper(), 1) for c in "asdfghjkl"],
     ("semicolon", ";", 1), ("quote", "'", 1), ("return", "Enter", 2.25)],
    [("left_shift", "Shift", 2.25), *[(c, c.upper(), 1) for c in "zxcvbnm"],
     ("comma", ",", 1), ("period", ".", 1), ("slash", "/", 1), ("right_shift", "Shift", 2.75)],
    [("left_control", "Ctrl", 1.25), ("left_command", "Win", 1.25), ("left_option", "Alt", 1.25),
     ("space", "Space", 6.25), ("right_option", "Alt", 1.25), (None, "Fn", 1.25),
     ("application", "Menu", 1.25), ("right_control", "Ctrl", 1.25)],
]

_NAV_ROWS: list[_Row] = [
    [("print_screen", "PrtSc", 1), ("scroll_lock", "ScrLk", 1), ("pause", "Pause", 1)],
    [("insert", "Ins", 1), ("home", "Home", 1), ("page_up", "PgUp", 1)],
    [("delete", "Del", 1), ("end", "End", 1), ("page_down", "PgDn", 1)],
    [],
    [(None, "", 1), ("up", "↑", 1)],
    [("left", "←", 1), ("down", "↓", 1), ("right", "→", 1)],
]


def _place(row: _Row, x: float, y: float) -> list[Key]:
    keys = []
    for name, legend, width in row:
        if legend:
            keys.append(Key(name, legend, x, y, width))
        x += width
    return keys


def _build() -> tuple[Key, ...]:
    keys: list[Key] = []
    row_y = [0.0] + [1 + GAP + i for i in range(len(_MAIN_ROWS))]
    for row, y in zip([_FUNCTION_ROW, *_MAIN_ROWS], row_y):
        keys += _place(row, 0, y)
    for row, y in zip(_NAV_ROWS, row_y):
        keys += _place(row, NAV_X, y)
    return tuple(keys)


KEYS: tuple[Key, ...] = _build()
BY_NAME: dict[str, Key] = {k.name: k for k in KEYS if k.name}
KEY_NAMES: list[str] = list(BY_NAME)
WIDTH = NAV_X + 3
HEIGHT = max(k.y for k in KEYS) + 1
