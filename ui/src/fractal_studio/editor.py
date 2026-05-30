from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QImage, QPaintEvent, QPainter, QMouseEvent, QPixmap
from PySide6.QtWidgets import QWidget

from fractal_studio.backend import BackendProfile, Color, CoreBackend
from fractal_studio.ui.controllers.editor_controller import DragState, EditorController


class PalettePreviewWidget(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._palette: list[Color] = []
        self.setMinimumHeight(84)
        self.setObjectName("palettePreview")

    def set_palette(self, palette: list[Color]) -> None:
        self._palette = list(palette)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())

        title_rect = QRectF(12, 8, self.width() - 24, 20)
        painter.setPen(self.palette().text().color())
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._title,
        )

        bar_rect = QRectF(12, 34, self.width() - 24, self.height() - 46)
        painter.fillRect(bar_rect, self.palette().base())
        if not self._palette:
            painter.drawText(
                bar_rect,
                Qt.AlignmentFlag.AlignCenter,
                "Add at least four control points.",
            )
            return

        width = max(1, int(bar_rect.width()))
        palette_size = len(self._palette)
        strip = QImage(width, 1, QImage.Format.Format_RGB32)
        for x in range(width):
            index = round(x * (palette_size - 1) / max(1, width - 1))
            red, green, blue = self._palette[index]
            strip.setPixelColor(x, 0, QColor(red, green, blue))

        pixmap = QPixmap.fromImage(strip).scaled(
            int(bar_rect.width()),
            int(bar_rect.height()),
        )
        painter.drawPixmap(bar_rect.toRect(), pixmap)


class ColorCubeEditor(QWidget):
    control_points_changed = Signal(list)
    palette_changed = Signal(list)
    status_changed = Signal(str)

    def __init__(
        self,
        backend: CoreBackend,
        profile: BackendProfile,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._profile = profile
        self._controller = EditorController(backend, profile)
        self._control_points: list[Color] = []
        self._palette: list[Color] = []
        self._drag_state: DragState | None = None
        self._face_pixmaps: dict[tuple[int, int], QPixmap] = {}
        self.setMinimumSize(520, 520)
        self.setMouseTracking(True)

    @property
    def control_points(self) -> list[Color]:
        return list(self._control_points)

    @property
    def generated_palette(self) -> list[Color]:
        return list(self._palette)

    def clear_points(self) -> None:
        self._controller.clear_points(self)

    def seed_points(self) -> None:
        self._controller.seed_points(self)

    def set_control_points(self, control_points: list[Color]) -> None:
        self._controller.set_control_points(self, control_points)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._face_pixmaps.clear()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._controller.handle_mouse_press(
                self, event.position().x(), event.position().y()
            )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._controller.handle_mouse_move(
            self, event.position().x(), event.position().y()
        )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._controller.handle_mouse_release(self)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        self._controller.paint(self, painter)
