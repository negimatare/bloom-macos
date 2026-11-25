"""Draw the Bloom app icon (the Lucide flower on a dark rounded square).

Writes src/bloom/assets/bloom.png and, with macOS's iconutil, bloom.icns:
    uv run python scripts/make_icon.py
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter

from bloom.gui import icons, theme

ASSETS = Path(__file__).resolve().parents[1] / "src" / "bloom" / "assets"
SIZE = 1024
BODY = 824  # Apple's icon grid: the shape fills 824 of 1024 pixels
RADIUS = 185


def draw(size: int) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    scale = size / SIZE
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    margin = (SIZE - BODY) / 2 * scale
    body = QRectF(margin, margin, BODY * scale, BODY * scale)
    gradient = QLinearGradient(body.topLeft(), body.bottomLeft())
    gradient.setColorAt(0, QColor("#2E2833"))
    gradient.setColorAt(1, QColor(theme.BACKGROUND))
    painter.setPen(QColor(theme.REMAPPED))
    painter.setBrush(gradient)
    painter.drawRoundedRect(body, RADIUS * scale, RADIUS * scale)
    flower = BODY * 0.62 * scale
    offset = (size - flower) / 2
    target = QRectF(offset, offset, flower, flower).toRect()
    painter.drawPixmap(target, icons.pixmap("flower", theme.ACCENT, max(16, round(flower))))
    painter.end()
    return image


def main() -> int:
    QGuiApplication(sys.argv)
    ASSETS.mkdir(parents=True, exist_ok=True)
    draw(SIZE).save(str(ASSETS / "bloom.png"))
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "bloom.iconset"
        iconset.mkdir()
        for points in (16, 32, 128, 256, 512):
            draw(points).save(str(iconset / f"icon_{points}x{points}.png"))
            draw(points * 2).save(str(iconset / f"icon_{points}x{points}@2x.png"))
        subprocess.run(["/usr/bin/iconutil", "-c", "icns", str(iconset),
                        "-o", str(ASSETS / "bloom.icns")], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
