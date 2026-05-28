from __future__ import annotations

from dataclasses import dataclass
from math import dist
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QImage, QPainter, QPen, QPixmap

from fractal_studio.backend import BackendProfile, Color, CoreBackend

if TYPE_CHECKING:
    from fractal_studio.editor import ColorCubeEditor

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


class EditorController:
    def __init__(self, backend: CoreBackend, profile: BackendProfile) -> None:
        self._backend = backend
        self._profile = profile

    def clear_points(self, editor: ColorCubeEditor) -> None:
        editor._control_points.clear()
        self.refresh_palette(editor)
        editor.update()

    def seed_points(self, editor: ColorCubeEditor) -> None:
        editor._control_points = [
            (16, 24, 48),
            (48, 96, 160),
            (120, 180, 220),
            (224, 180, 96),
            (255, 240, 200),
        ]
        self.refresh_palette(editor)
        editor.update()

    def set_control_points(
        self, editor: ColorCubeEditor, control_points: list[Color]
    ) -> None:
        editor._control_points = list(control_points)
        self.refresh_palette(editor)
        editor.update()

    def refresh_palette(self, editor: ColorCubeEditor) -> None:
        editor._palette = (
            self._backend.generate_palette(
                editor._control_points, self._profile.palette_size
            )
            if self._backend.available
            else []
        )
        editor.control_points_changed.emit(list(editor._control_points))
        editor.palette_changed.emit(list(editor._palette))

    def handle_mouse_press(self, editor: ColorCubeEditor, x: float, y: float) -> None:
        if not self._backend.available:
            return

        face, position = self.face_at(editor, QPointF(x, y))
        if face is None or position is None:
            return

        point_index = self.nearest_point(editor, face, QPointF(x, y))
        if point_index is None:
            editor._control_points.append(self._backend.color_from_face(face, position))
            self.refresh_palette(editor)
            editor.status_changed.emit(
                f"Added control point {len(editor._control_points) - 1} on face {face}."
            )
            editor.update()
            return

        editor._drag_state = DragState(face=face, point_index=point_index)
        editor.status_changed.emit(
            f"Dragging control point {point_index} on face {face}."
        )

    def handle_mouse_move(self, editor: ColorCubeEditor, x: float, y: float) -> None:
        face, position = self.face_at(editor, QPointF(x, y))
        if face is not None and position is not None and editor._drag_state is None:
            red, green, blue = (
                self._backend.color_from_face(face, position)
                if self._backend.available
                else (0, 0, 0)
            )
            editor.status_changed.emit(f"Face {face}: {red}, {green}, {blue}")

        if editor._drag_state is None or face is None or position is None:
            return

        if face != editor._drag_state.face:
            return

        index = editor._drag_state.point_index
        current = editor._control_points[index]
        editor._control_points[index] = self._backend.update_control_point_from_face(
            face, current, position
        )
        self.refresh_palette(editor)
        editor.update()

    def handle_mouse_release(self, editor: ColorCubeEditor) -> None:
        editor._drag_state = None

    def paint(self, editor: ColorCubeEditor, painter: QPainter) -> None:
        painter.fillRect(editor.rect(), editor.palette().window())

        for face, rect in self.face_rects(editor).items():
            painter.drawPixmap(
                rect.toRect(), self.face_pixmap(editor, face, rect.size().toSize())
            )
            painter.setPen(editor.palette().shadow().color())
            painter.drawRect(rect)
            painter.setPen(editor.palette().text().color())
            painter.drawText(rect.adjusted(8, 6, -8, -6), FACE_LABELS[face])

        if len(editor._control_points) >= 4:
            for face in ACTIVE_FACES:
                self.draw_spline(editor, painter, face)

        for face in ACTIVE_FACES:
            self.draw_points(editor, painter, face)

        if not self._backend.available:
            painter.setPen(editor.palette().text().color())
            painter.drawText(
                editor.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Build the Rust extension to enable editing.",
            )

    def face_rects(self, editor: ColorCubeEditor) -> dict[int, QRectF]:
        margin = 12.0
        size = min(
            (editor.width() - margin * 2) / 3.0, (editor.height() - margin * 2) / 3.0
        )
        total_width = size * 3.0
        total_height = size * 3.0
        origin_x = (editor.width() - total_width) / 2.0
        origin_y = (editor.height() - total_height) / 2.0

        return {
            face: QRectF(origin_x + column * size, origin_y + row * size, size, size)
            for face, (column, row) in ACTIVE_FACES.items()
        }

    def face_at(
        self, editor: ColorCubeEditor, point: QPointF
    ) -> tuple[int | None, tuple[float, float] | None]:
        for face, rect in self.face_rects(editor).items():
            if rect.contains(point):
                x = (point.x() - rect.left()) / max(1.0, rect.width())
                y = (point.y() - rect.top()) / max(1.0, rect.height())
                return face, (min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0))
        return None, None

    def face_pixmap(self, editor: ColorCubeEditor, face: int, size) -> QPixmap:
        key = (face, size.width(), size.height())
        if key in editor._face_pixmaps:
            return editor._face_pixmaps[key]

        image = QImage(size.width(), size.height(), QImage.Format.Format_RGB32)
        for y in range(size.height()):
            normalized_y = y / max(1, size.height() - 1)
            for x in range(size.width()):
                normalized_x = x / max(1, size.width() - 1)
                red, green, blue = self._backend.color_from_face(
                    face, (normalized_x, normalized_y)
                )
                image.setPixelColor(x, y, QColor(red, green, blue))

        pixmap = QPixmap.fromImage(image)
        editor._face_pixmaps[key] = pixmap
        return pixmap

    def nearest_point(
        self, editor: ColorCubeEditor, face: int, point: QPointF
    ) -> int | None:
        candidates = []
        for index, color in enumerate(editor._control_points):
            projected = self.projected_point(editor, face, color)
            candidates.append(
                (index, dist((projected.x(), projected.y()), (point.x(), point.y())))
            )

        if not candidates:
            return None

        index, distance = min(candidates, key=lambda item: item[1])
        return index if distance <= 14.0 else None

    def projected_point(
        self, editor: ColorCubeEditor, face: int, color: Color
    ) -> QPointF:
        rect = self.face_rects(editor)[face]
        x, y = self._backend.project_color_to_face(face, color)
        return QPointF(rect.left() + x * rect.width(), rect.top() + y * rect.height())

    def draw_points(
        self, editor: ColorCubeEditor, painter: QPainter, face: int
    ) -> None:
        metrics = QFontMetrics(painter.font())
        for index, color in enumerate(editor._control_points):
            point = self.projected_point(editor, face, color)
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.setBrush(QColor(*color))
            painter.drawEllipse(point, 5, 5)
            text = str(index)
            painter.setPen(editor.palette().text().color())
            painter.drawText(
                QRectF(
                    point.x() + 6,
                    point.y() - metrics.height() / 2,
                    20,
                    metrics.height(),
                ),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text,
            )

    def draw_spline(
        self, editor: ColorCubeEditor, painter: QPainter, face: int
    ) -> None:
        projected = [
            self.projected_point(editor, face, color)
            for color in editor._control_points
        ]
        pen = QPen(editor.palette().highlight().color(), 2)
        painter.setPen(pen)

        for segment_index in range(len(projected) - 3):
            previous = projected[segment_index + 1]
            for sample_index in range(1, 33):
                t = sample_index / 32.0
                current = self.catmull_rom_point(
                    projected[segment_index],
                    projected[segment_index + 1],
                    projected[segment_index + 2],
                    projected[segment_index + 3],
                    t,
                )
                painter.drawLine(previous, current)
                previous = current

    def catmull_rom_point(
        self,
        p0: QPointF,
        p1: QPointF,
        p2: QPointF,
        p3: QPointF,
        t: float,
    ) -> QPointF:
        return QPointF(
            self.catmull_rom_channel(p0.x(), p1.x(), p2.x(), p3.x(), t),
            self.catmull_rom_channel(p0.y(), p1.y(), p2.y(), p3.y(), t),
        )

    def catmull_rom_channel(
        self, p0: float, p1: float, p2: float, p3: float, t: float
    ) -> float:
        return 0.5 * (
            (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t * t * t
            + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t
            + (-p0 + p2) * t
            + 2.0 * p1
        )
