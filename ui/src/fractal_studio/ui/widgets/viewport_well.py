from __future__ import annotations

import math

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPolygon, QResizeEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from fractal_studio.theme import ThemeSpec
from fractal_studio.viewport import FractalViewportWidget

_TILE = 22  # size of each checkerboard tile in pixels


class ViewportWell(QWidget):
    """Wraps FractalViewportWidget with a diagonal-checkerboard dead-space background.

    The viewport is centred; Qt's hasHeightForWidth propagation maintains the
    chosen aspect ratio. Leftover space fills with the subtle checker pattern.
    A floating hint label is positioned bottom-left via resizeEvent.
    """

    def __init__(
        self,
        viewport: FractalViewportWidget,
        theme: ThemeSpec,
        hint_label: QLabel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._viewport = viewport
        self._hint = hint_label
        self._build_layout()
        self._adopt_hint(hint_label)

    # --- public API ---

    def set_theme(self, spec: ThemeSpec) -> None:
        self._theme = spec
        self.update()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._viewport.heightForWidth(width)

    # --- Qt overrides ---

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._reposition_hint()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        self._draw_checkerboard(painter)
        painter.end()

    # --- private ---

    def _build_layout(self) -> None:
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        hbox.addWidget(self._viewport, 0, Qt.AlignmentFlag.AlignCenter)
        vbox.addLayout(hbox, 1)
        self.setLayout(vbox)

    def _adopt_hint(self, hint_label: QLabel) -> None:
        hint_label.setParent(self)
        hint_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        hint_label.raise_()
        hint_label.show()  # show once on adoption; caller may hide() thereafter

    def _reposition_hint(self) -> None:
        margin = 10
        self._hint.adjustSize()
        x = margin
        y = self.height() - self._hint.sizeHint().height() - margin
        self._hint.move(x, max(0, y))

    def _draw_checkerboard(self, painter: QPainter) -> None:
        """Draw a 45°-rotated checkerboard across the full widget area."""
        ca = QColor(self._theme.checker_a)
        cb = QColor(self._theme.checker_b)
        w, h = self.width(), self.height()

        painter.fillRect(0, 0, w, h, ca)

        half = _TILE // 2
        rows = math.ceil(h / _TILE) + 2
        cols = math.ceil(w / _TILE) + 2

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(cb)

        for row in range(-1, rows):
            for col in range(-1, cols):
                cx = col * _TILE + (half if row % 2 else 0)
                cy = row * _TILE
                diamond = QPolygon([
                    QPoint(cx, cy - half),
                    QPoint(cx + half, cy),
                    QPoint(cx, cy + half),
                    QPoint(cx - half, cy),
                ])
                painter.drawPolygon(diamond)
