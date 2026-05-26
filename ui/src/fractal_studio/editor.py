from __future__ import annotations

from dataclasses import dataclass
from math import dist

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QImage, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from fractal_studio.backend import BackendProfile, Color, CoreBackend

ACTIVE_FACES: dict[int, tuple[int, int]] = {
    2: (0, 0),
    1: (1, 0),
    3: (0, 1),
    6: (2, 1),
    4: (1, 2),
    5: (2, 2),
}
FACE_LABELS = {
    1: "R=255",
    2: "G=255",
    3: "B=255",
    4: "R=0",
    5: "G=0",
    6: "B=0",
}


@dataclass(frozen=True)
class DragState:
    face: int
    point_index: int


class PalettePreviewWidget(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._palette: list[Color] = []
        self.setMinimumHeight(84)

    def set_palette(self, palette: list[Color]) -> None:
        self._palette = list(palette)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        painter.setPen(self.palette().mid().color())
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        title_rect = QRectF(12, 8, self.width() - 24, 20)
        painter.setPen(self.palette().text().color())
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._title)

        bar_rect = QRectF(12, 34, self.width() - 24, self.height() - 46)
        painter.fillRect(bar_rect, self.palette().base())
        if not self._palette:
            painter.drawText(bar_rect, Qt.AlignmentFlag.AlignCenter, "Add at least four control points.")
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

    def __init__(self, backend: CoreBackend, profile: BackendProfile, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._profile = profile
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
        self._control_points.clear()
        self._refresh_palette()
        self.update()

    def seed_points(self) -> None:
        self._control_points = [
            (16, 24, 48),
            (48, 96, 160),
            (120, 180, 220),
            (224, 180, 96),
            (255, 240, 200),
        ]
        self._refresh_palette()
        self.update()

    def set_control_points(self, control_points: list[Color]) -> None:
        self._control_points = list(control_points)
        self._refresh_palette()
        self.update()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._face_pixmaps.clear()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._backend.available or event.button() != Qt.MouseButton.LeftButton:
            return

        face, position = self._face_at(event.position())
        if face is None or position is None:
            return

        point_index = self._nearest_point(face, event.position())
        if point_index is None:
            self._control_points.append(self._backend.color_from_face(face, position))
            self._refresh_palette()
            self.status_changed.emit(f"Added control point {len(self._control_points) - 1} on face {face}.")
            self.update()
            return

        self._drag_state = DragState(face=face, point_index=point_index)
        self.status_changed.emit(f"Dragging control point {point_index} on face {face}.")

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        face, position = self._face_at(event.position())
        if face is not None and position is not None and self._drag_state is None:
            red, green, blue = self._backend.color_from_face(face, position) if self._backend.available else (0, 0, 0)
            self.status_changed.emit(f"Face {face}: {red}, {green}, {blue}")

        if self._drag_state is None or face is None or position is None:
            return

        if face != self._drag_state.face:
            return

        index = self._drag_state.point_index
        current = self._control_points[index]
        self._control_points[index] = self._backend.update_control_point_from_face(face, current, position)
        self._refresh_palette()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_state = None

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())

        for face, rect in self._face_rects().items():
            painter.drawPixmap(rect.toRect(), self._face_pixmap(face, rect.size().toSize()))
            painter.setPen(self.palette().shadow().color())
            painter.drawRect(rect)
            painter.setPen(self.palette().text().color())
            painter.drawText(rect.adjusted(8, 6, -8, -6), FACE_LABELS[face])

        if len(self._control_points) >= 4:
            for face in ACTIVE_FACES:
                self._draw_spline(painter, face)

        for face in ACTIVE_FACES:
            self._draw_points(painter, face)

        if not self._backend.available:
            painter.setPen(self.palette().text().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Build the Rust extension to enable editing.")

    def _refresh_palette(self) -> None:
        self._palette = (
            self._backend.generate_palette(self._control_points, self._profile.palette_size)
            if self._backend.available
            else []
        )
        self.control_points_changed.emit(list(self._control_points))
        self.palette_changed.emit(list(self._palette))

    def _face_rects(self) -> dict[int, QRectF]:
        margin = 12.0
        size = min((self.width() - margin * 2) / 3.0, (self.height() - margin * 2) / 3.0)
        total_width = size * 3.0
        total_height = size * 3.0
        origin_x = (self.width() - total_width) / 2.0
        origin_y = (self.height() - total_height) / 2.0

        return {
            face: QRectF(origin_x + column * size, origin_y + row * size, size, size)
            for face, (column, row) in ACTIVE_FACES.items()
        }

    def _face_at(self, point: QPointF) -> tuple[int | None, tuple[float, float] | None]:
        for face, rect in self._face_rects().items():
            if rect.contains(point):
                x = (point.x() - rect.left()) / max(1.0, rect.width())
                y = (point.y() - rect.top()) / max(1.0, rect.height())
                return face, (min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0))
        return None, None

    def _face_pixmap(self, face: int, size) -> QPixmap:
        key = (face, size.width(), size.height())
        if key in self._face_pixmaps:
            return self._face_pixmaps[key]

        image = QImage(size.width(), size.height(), QImage.Format.Format_RGB32)
        for y in range(size.height()):
            normalized_y = y / max(1, size.height() - 1)
            for x in range(size.width()):
                normalized_x = x / max(1, size.width() - 1)
                red, green, blue = self._backend.color_from_face(face, (normalized_x, normalized_y))
                image.setPixelColor(x, y, QColor(red, green, blue))

        pixmap = QPixmap.fromImage(image)
        self._face_pixmaps[key] = pixmap
        return pixmap

    def _nearest_point(self, face: int, point: QPointF) -> int | None:
        candidates = []
        for index, color in enumerate(self._control_points):
            projected = self._projected_point(face, color)
            candidates.append((index, dist((projected.x(), projected.y()), (point.x(), point.y()))))

        if not candidates:
            return None

        index, distance = min(candidates, key=lambda item: item[1])
        return index if distance <= 14.0 else None

    def _projected_point(self, face: int, color: Color) -> QPointF:
        rect = self._face_rects()[face]
        x, y = self._backend.project_color_to_face(face, color)
        return QPointF(rect.left() + x * rect.width(), rect.top() + y * rect.height())

    def _draw_points(self, painter: QPainter, face: int) -> None:
        metrics = QFontMetrics(painter.font())
        for index, color in enumerate(self._control_points):
            point = self._projected_point(face, color)
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.setBrush(QColor(*color))
            painter.drawEllipse(point, 5, 5)
            text = str(index)
            painter.setPen(self.palette().text().color())
            painter.drawText(
                QRectF(point.x() + 6, point.y() - metrics.height() / 2, 20, metrics.height()),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text,
            )

    def _draw_spline(self, painter: QPainter, face: int) -> None:
        projected = [self._projected_point(face, color) for color in self._control_points]
        pen = QPen(self.palette().highlight().color(), 2)
        painter.setPen(pen)

        for segment_index in range(len(projected) - 3):
            previous = projected[segment_index + 1]
            for sample_index in range(1, 33):
                t = sample_index / 32.0
                current = self._catmull_rom_point(
                    projected[segment_index],
                    projected[segment_index + 1],
                    projected[segment_index + 2],
                    projected[segment_index + 3],
                    t,
                )
                painter.drawLine(previous, current)
                previous = current

    def _catmull_rom_point(
        self,
        p0: QPointF,
        p1: QPointF,
        p2: QPointF,
        p3: QPointF,
        t: float,
    ) -> QPointF:
        return QPointF(
            self._catmull_rom_channel(p0.x(), p1.x(), p2.x(), p3.x(), t),
            self._catmull_rom_channel(p0.y(), p1.y(), p2.y(), p3.y(), t),
        )

    def _catmull_rom_channel(self, p0: float, p1: float, p2: float, p3: float, t: float) -> float:
        return 0.5 * (
            (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t * t * t
            + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t
            + (-p0 + p2) * t
            + 2.0 * p1
        )
