from __future__ import annotations

import base64

from PySide6.QtCore import QBuffer, QByteArray, Qt
from PySide6.QtGui import QColor, QPixmap


def encode_pixmap(pixmap: QPixmap) -> str:
    scaled = pixmap.scaled(
        96,
        72,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    scaled.toImage().save(buf, "PNG")
    buf.close()
    return base64.b64encode(bytes(ba)).decode()


def decode_thumbnail(b64: str) -> QPixmap:
    pixmap = QPixmap()
    pixmap.loadFromData(base64.b64decode(b64))
    return pixmap


def placeholder_pixmap() -> QPixmap:
    pixmap = QPixmap(48, 36)
    pixmap.fill(QColor("#313244"))
    return pixmap
