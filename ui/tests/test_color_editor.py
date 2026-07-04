from __future__ import annotations

import gc
import tempfile
import unittest
import json
from dataclasses import replace
from pathlib import Path

import pytest

from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QComboBox, QSpinBox
from tests.support import (
    DummyEditorBackend,
    DummyPaletteBackend,
    DummyUnavailableBackend,
    QtWindowTestCase,
    _FULL_CAPS,
    get_app,
)


@pytest.mark.integration
class TestThumbnailHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_app()

    def test_encode_decode_round_trip(self) -> None:
        from fractal_studio.thumbnail_utils import decode_thumbnail, encode_pixmap
        from PySide6.QtGui import QColor, QPixmap

        original = QPixmap(96, 72)
        original.fill(QColor("#ff0000"))
        b64 = encode_pixmap(original)
        result = decode_thumbnail(b64)
        self.assertEqual(result.width(), 96)
        self.assertEqual(result.height(), 72)
        self.assertFalse(result.isNull())

    def test_placeholder_pixmap_correct_size(self) -> None:
        from fractal_studio.thumbnail_utils import placeholder_pixmap

        p = placeholder_pixmap()
        self.assertEqual(p.width(), 48)
        self.assertEqual(p.height(), 36)
        self.assertFalse(p.isNull())

    def test_encode_pixmap_returns_valid_base64(self) -> None:
        from fractal_studio.thumbnail_utils import encode_pixmap
        from PySide6.QtGui import QColor, QPixmap
        import base64

        pixmap = QPixmap(200, 150)
        pixmap.fill(QColor("#00ff00"))
        b64 = encode_pixmap(pixmap)
        decoded = base64.b64decode(b64)
        self.assertGreater(len(decoded), 0)
        self.assertTrue(decoded[:4] == b"\x89PNG")


@pytest.mark.integration
class TestColorCubeEditor(unittest.TestCase):
    _ACTIVE_FACE_GRID = {
        2: (0, 0),
        1: (1, 0),
        3: (0, 1),
        6: (2, 1),
        4: (1, 2),
        5: (2, 2),
    }

    @classmethod
    def setUpClass(cls) -> None:
        get_app()

    def _make_editor(self, backend=None):
        from fractal_studio.editor import ColorCubeEditor
        from fractal_studio.backend import default_profile

        editor = ColorCubeEditor(backend or DummyEditorBackend(), default_profile())
        editor.resize(540, 540)
        editor.show()
        return editor

    def _point(self, point) -> tuple[int, int]:
        return (round(point.x()), round(point.y()))

    def _face_rect(self, editor, face: int) -> tuple[float, float, float, float]:
        margin = 12.0
        size = min(
            (editor.width() - margin * 2) / 3.0, (editor.height() - margin * 2) / 3.0
        )
        origin_x = (editor.width() - size * 3.0) / 2.0
        origin_y = (editor.height() - size * 3.0) / 2.0
        column, row = self._ACTIVE_FACE_GRID[face]
        left = origin_x + column * size
        top = origin_y + row * size
        return (left, top, size, size)

    def _point_for_color(self, editor, face: int, color: tuple[int, int, int]):
        from PySide6.QtCore import QPoint

        x, y = DummyEditorBackend().project_color_to_face(face, color)
        left, top, size, _ = self._face_rect(editor, face)
        return QPoint(round(left + x * size), round(top + y * size))

    def _face_center_point(self, editor, face: int):
        from PySide6.QtCore import QPoint

        left, top, size, _ = self._face_rect(editor, face)
        return QPoint(round(left + size / 2.0), round(top + size / 2.0))

    def _click(self, editor, point) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        QTest.mouseClick(
            editor, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point
        )

    def _press(self, editor, point) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        QTest.mousePress(
            editor, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point
        )

    def _move(self, editor, point) -> None:
        from PySide6.QtTest import QTest

        QTest.mouseMove(editor, point)

    def _release(self, editor, point) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        QTest.mouseRelease(
            editor, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point
        )

    def test_seed_clear_and_palette_refresh(self) -> None:
        editor = self._make_editor()
        changed: list[list[tuple[int, int, int]]] = []
        editor.palette_changed.connect(changed.append)

        editor.seed_points()
        self.assertGreaterEqual(len(editor.control_points), 4)
        editor.clear_points()
        self.assertEqual(editor.control_points, [])
        self.assertEqual(changed[-1], [])

    def test_click_outside_faces_does_not_add_point(self) -> None:
        from PySide6.QtCore import QPoint

        editor = self._make_editor()
        outside = QPoint(2, 2)
        self._click(editor, outside)

        self.assertEqual(editor.control_points, [])

    def test_mouse_press_drag_and_move_updates_point(self) -> None:
        from PySide6.QtCore import QPoint

        editor = self._make_editor()
        statuses: list[str] = []
        editor.status_changed.connect(statuses.append)
        editor.set_control_points([(10, 10, 10)])
        start = self._point_for_color(editor, 2, (10, 10, 10))
        end = QPoint(start.x() + 8, start.y() + 8)
        self._press(editor, start)
        self._move(editor, end)
        self.assertNotEqual(editor.control_points[0], (10, 10, 10))
        self._release(editor, end)
        self.assertTrue(
            any(
                status.startswith("Dragging control point 0 on face 2")
                for status in statuses
            )
        )

    def test_mouse_press_adds_point_and_hover_status(self) -> None:
        editor = self._make_editor()
        statuses: list[str] = []
        editor.status_changed.connect(statuses.append)
        pos = self._face_center_point(editor, 2)
        self._click(editor, pos)
        self.assertEqual(len(editor.control_points), 1)
        self.assertTrue(
            any(
                status.startswith("Added control point 0 on face 2")
                for status in statuses
            )
        )

    def test_paint_event_handles_backend_missing(self) -> None:
        editor = self._make_editor(backend=DummyUnavailableBackend())
        editor.paintEvent(QPaintEvent(editor.rect()))


