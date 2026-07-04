from __future__ import annotations

import sys
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from fractal_studio.backend import BackendCapabilities

_FULL_CAPS = BackendCapabilities(
    can_render=True,
    can_generate_palette=True,
    can_import_palette=True,
    can_export_palette=True,
)
_NO_CAPS = BackendCapabilities(
    can_render=False,
    can_generate_palette=False,
    can_import_palette=False,
    can_export_palette=False,
)

_APP: QApplication | None = None


def get_app() -> QApplication:
    global _APP
    if QApplication.instance() is None:
        _APP = QApplication([])
    return QApplication.instance()


class QtWindowTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_app()

    def make_window(self):
        from fractal_studio.main_window_factory import create_main_window

        window = create_main_window()
        self.addCleanup(window.close)
        return window


class DummyEditorBackend:
    available = True
    capabilities = _FULL_CAPS

    def color_from_face(
        self, face: int, position: tuple[float, float]
    ) -> tuple[int, int, int]:
        x, y = position
        return (face * 10 + int(x * 10), face * 10 + int(y * 10), face * 10)

    def project_color_to_face(
        self, face: int, color: tuple[int, int, int]
    ) -> tuple[float, float]:
        return ((color[0] % 10) / 10.0, (color[1] % 10) / 10.0)

    def update_control_point_from_face(
        self,
        face: int,
        color: tuple[int, int, int],
        position: tuple[float, float],
    ) -> tuple[int, int, int]:
        x, y = position
        return (face * 10 + int(x * 10), face * 10 + int(y * 10), color[2])

    def generate_palette(
        self, control_points: list[tuple[int, int, int]], palette_size: int
    ) -> list[tuple[int, int, int]]:
        return control_points[:palette_size]


class DummyUnavailableBackend(DummyEditorBackend):
    available = False
    capabilities = _NO_CAPS


class DummyPaletteBackend:
    available = True
    capabilities = _FULL_CAPS

    def __init__(self) -> None:
        self.saved: list[tuple[str, list[tuple[int, int, int]], int]] = []
        self.loaded_paths: list[str] = []
        self.exported: list[tuple[str, list[tuple[int, int, int]]]] = []

    def export_palette_json(
        self, path: str, control_points: list[tuple[int, int, int]], palette_size: int
    ) -> None:
        self.saved.append((path, list(control_points), palette_size))

    def import_palette_json(self, path: str) -> tuple[int, list[tuple[int, int, int]]]:
        self.loaded_paths.append(path)
        return 6, [(1, 2, 3), (4, 5, 6)]

    def generate_palette(
        self, control_points: list[tuple[int, int, int]], palette_size: int
    ) -> list[tuple[int, int, int]]:
        self.exported.append(("generated", list(control_points)))
        return list(control_points[:palette_size])

    def export_legacy_map(self, path: str, palette: list[tuple[int, int, int]]) -> None:
        self.exported.append((path, list(palette)))
