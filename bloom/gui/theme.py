"""Bloom's dark, desaturated pink look: palette tokens and one stylesheet."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

BACKGROUND = "#171519"
PANEL = "#242027"
KEY = "#343039"
REMAPPED = "#493145"
REMAPPED_BORDER = "#7A5A70"
ACCENT = "#E6A0CD"
ON_ACCENT = "#2A1A26"
TEXT = "#EDE8EE"
MUTED = "#9C94A0"
DISABLED = "#625B66"
BORDER = "#332E37"
BORDER_STRONG = "#443D49"
SUCCESS = "#7FC8A0"
ERROR = "#E8918F"

_CHEVRON = Path(__file__).with_name("chevron-down.svg").as_posix()

STYLESHEET = f"""
QWidget {{ background: {BACKGROUND}; color: {TEXT}; font-size: 13px; }}
QLabel, QCheckBox {{ background: transparent; }}
QToolTip {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER_STRONG}; padding: 4px 6px; }}

QFrame#topbar {{ border-bottom: 1px solid {BORDER}; }}
QFrame[role="card"] {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame[role="card"] QWidget {{ background: transparent; }}
QFrame[role="card"][active="true"] {{ border-color: {ACCENT}; background: #2B2330; }}
QFrame[role="card"] QFrame[role="separator"] {{ background: {BORDER}; max-height: 1px; min-height: 1px; }}

QLabel[role="wordmark"] {{ color: {ACCENT}; font-size: 16px; font-weight: 600; letter-spacing: 1px; }}
QLabel[role="title"] {{ font-size: 21px; font-weight: 600; }}
QLabel[role="heading"] {{ font-size: 14px; font-weight: 600; }}
QLabel[role="muted"] {{ color: {MUTED}; font-size: 12px; }}
QLabel[role="badge"] {{
    background: {REMAPPED}; color: {ACCENT}; border-radius: 8px; padding: 5px 12px; font-size: 12px;
}}
QLabel[role="accent"] {{ color: {ACCENT}; }}
QLabel[role="value"] {{ color: {ACCENT}; font-size: 18px; font-weight: 600; }}

QPushButton {{
    background: {PANEL}; border: 1px solid {BORDER_STRONG}; border-radius: 8px;
    padding: 6px 14px;
}}
QPushButton:hover {{ border-color: {MUTED}; }}
QPushButton:disabled {{ color: {DISABLED}; border-color: {BORDER}; }}
QPushButton[role="primary"] {{ background: {ACCENT}; color: {ON_ACCENT}; border: none; font-weight: 600; }}
QPushButton[role="primary"]:disabled {{ background: {KEY}; color: {MUTED}; }}
QFrame[role="card"] QPushButton[role="primary"] {{ background: {ACCENT}; }}
QFrame[role="card"] QPushButton[role="primary"]:disabled {{ background: {KEY}; }}
QPushButton[role="flat"] {{ background: transparent; border: none; color: {MUTED}; padding: 4px 6px; }}
QPushButton[role="flat"]:hover {{ color: {TEXT}; }}
QPushButton[role="flat"]:disabled {{ color: {DISABLED}; }}
QPushButton[role="flat-heading"] {{
    background: transparent; border: none; padding: 4px 0; font-size: 14px; font-weight: 600; text-align: left;
}}
QPushButton[role="nav"] {{
    background: transparent; border: none; border-radius: 8px; padding: 6px 14px; color: {MUTED};
}}
QPushButton[role="nav"]:hover {{ color: {TEXT}; }}
QPushButton[role="nav"]:checked {{ background: {REMAPPED}; color: {ACCENT}; font-weight: 600; }}
QPushButton[role="preset"] {{ padding: 10px; border-radius: 10px; background: {BACKGROUND}; }}
QPushButton[role="preset"]:checked {{ background: {REMAPPED}; border-color: {ACCENT}; }}
QPushButton[role="segment"] {{ padding: 5px 14px; background: {BACKGROUND}; color: {MUTED}; }}
QPushButton[role="segment"]:checked {{ background: {REMAPPED}; border-color: {ACCENT}; color: {ACCENT}; }}

QComboBox {{
    background: {PANEL}; border: 1px solid {BORDER_STRONG}; border-radius: 8px;
    padding: 5px 10px; min-width: 120px;
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: url("{_CHEVRON}"); width: 14px; height: 14px; }}
QComboBox QAbstractItemView {{
    background: {PANEL}; border: 1px solid {BORDER_STRONG};
    selection-background-color: {REMAPPED}; selection-color: {ACCENT};
}}

QSlider:horizontal {{ min-height: 24px; }}  /* room for the 18px handle above and below the groove */
QSlider::groove:horizontal {{ height: 6px; background: {KEY}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
QSlider::sub-page:horizontal:disabled {{ background: {DISABLED}; }}
QSlider::handle:horizontal {{
    background: #FFFFFF; width: 18px; height: 18px; margin: -6px 0; border-radius: 9px;
}}

QProgressBar {{ background: {KEY}; border: none; border-radius: 3px; max-height: 6px; min-height: 6px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
QDialog {{ background: {PANEL}; }}
"""


def apply(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    for role, colour in [
        (QPalette.Window, BACKGROUND), (QPalette.WindowText, TEXT),
        (QPalette.Base, PANEL), (QPalette.AlternateBase, KEY),
        (QPalette.Text, TEXT), (QPalette.Button, PANEL), (QPalette.ButtonText, TEXT),
        (QPalette.Highlight, REMAPPED), (QPalette.HighlightedText, ACCENT),
        (QPalette.ToolTipBase, PANEL), (QPalette.ToolTipText, TEXT),
        (QPalette.PlaceholderText, MUTED),
    ]:
        palette.setColor(role, QColor(colour))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(DISABLED))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(DISABLED))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(DISABLED))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)
