from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QApplication

_APP: QApplication | None = None


def _get_app() -> QApplication:
    global _APP
    if QApplication.instance() is None:
        _APP = QApplication([])
    return QApplication.instance()


class QtWindowTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def make_window(self):
        from fractal_studio.main_window import MainWindow

        window = MainWindow()
        self.addCleanup(window.close)
        return window


class DummyEditorBackend:
    available = True

    def color_from_face(self, face: int, position: tuple[float, float]) -> tuple[int, int, int]:
        x, y = position
        return (face * 10 + int(x * 10), face * 10 + int(y * 10), face * 10)

    def project_color_to_face(self, face: int, color: tuple[int, int, int]) -> tuple[float, float]:
        return ((color[0] % 10) / 10.0, (color[1] % 10) / 10.0)

    def update_control_point_from_face(
        self,
        face: int,
        color: tuple[int, int, int],
        position: tuple[float, float],
    ) -> tuple[int, int, int]:
        x, y = position
        return (face * 10 + int(x * 10), face * 10 + int(y * 10), color[2])

    def generate_palette(self, control_points: list[tuple[int, int, int]], palette_size: int) -> list[tuple[int, int, int]]:
        return control_points[:palette_size]


class DummyUnavailableBackend(DummyEditorBackend):
    available = False


class TestCustomResolutionDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def test_default_values(self) -> None:
        from fractal_studio.main_window import CustomResolutionDialog

        dlg = CustomResolutionDialog(1920, 1080)
        self.assertEqual(dlg.values(), (1920, 1080))

    def test_custom_values(self) -> None:
        from fractal_studio.main_window import CustomResolutionDialog

        dlg = CustomResolutionDialog(3840, 2160)
        self.assertEqual(dlg.values(), (3840, 2160))

    def test_spinbox_range(self) -> None:
        from fractal_studio.main_window import CustomResolutionDialog

        dlg = CustomResolutionDialog(1920, 1080)
        dlg._width_box.setValue(0)
        dlg._height_box.setValue(-1)
        self.assertEqual(dlg.values(), (64, 64))

        dlg._width_box.setValue(99999)
        dlg._height_box.setValue(99999)
        self.assertEqual(dlg.values(), (16384, 16384))


class TestExportPanel(QtWindowTestCase):
    def test_export_combo_has_four_items(self) -> None:
        w = self.make_window()
        self.assertEqual(w._export_combo.count(), 4)

    def test_export_combo_last_item_is_custom(self) -> None:
        w = self.make_window()
        self.assertIn("Custom", w._export_combo.itemText(3))

    def test_export_combo_default_is_square(self) -> None:
        w = self.make_window()
        self.assertEqual(w._export_combo.currentIndex(), 0)
        self.assertIn("1080 × 1080", w._export_combo.itemText(0))

    def test_aspect_ratio_combo_has_three_modes(self) -> None:
        w = self.make_window()
        self.assertEqual(w._aspect_ratio_combo.count(), 3)
        expected_labels = ["(1:1)", "(3:4)", "(4:3)"]
        for index, suffix in enumerate(expected_labels):
            with self.subTest(index=index):
                self.assertIn(suffix, w._aspect_ratio_combo.itemText(index))

    def test_export_presets_follow_aspect_ratio(self) -> None:
        w = self.make_window()
        scenarios = [
            (0, "1080 × 1080"),
            (1, "1080 × 1440"),
            (2, "1440 × 1080"),
        ]

        for index, expected in scenarios:
            with self.subTest(aspect=index):
                w._aspect_ratio_combo.setCurrentIndex(index)
                self.assertIn(expected, w._export_combo.itemText(0))

    def test_unknown_aspect_ratio_defaults_to_square_presets(self) -> None:
        w = self.make_window()
        self.assertEqual(
            w._build_export_presets_for_mode("unexpected")[0],
            ("1080 × 1080", 1080, 1080),
        )

    def test_custom_size_row_hidden_by_default(self) -> None:
        w = self.make_window()
        self.assertTrue(w._custom_width_box.parentWidget().isHidden())

    def test_custom_size_row_shown_for_custom_preset(self) -> None:
        w = self.make_window()
        w._export_combo.setCurrentIndex(3)
        self.assertFalse(w._custom_width_box.parentWidget().isHidden())

    def test_export_uses_inline_custom_dimensions(self) -> None:
        from fractal_studio.main_window import MainWindow

        captured: list[tuple[int, int]] = []
        original = MainWindow._export_render
        try:
            MainWindow._export_render = lambda self, width, height: captured.append((width, height))
            w = self.make_window()
            w._export_combo.setCurrentIndex(3)
            w._custom_width_box.setValue(1234)
            w._custom_height_box.setValue(567)
            w._on_export_clicked()
            self.assertEqual(captured, [(1234, 567)])
        finally:
            MainWindow._export_render = original

    def test_export_uses_selected_square_preset_dimensions(self) -> None:
        from fractal_studio.main_window import MainWindow

        captured: list[tuple[int, int]] = []
        original = MainWindow._export_render
        try:
            MainWindow._export_render = lambda self, width, height: captured.append((width, height))
            w = self.make_window()
            w._export_combo.setCurrentIndex(0)
            w._on_export_clicked()
            self.assertEqual(captured, [(1080, 1080)])
        finally:
            MainWindow._export_render = original


class TestParamsPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def setUp(self) -> None:
        from fractal_studio.viewport import FractalParamsPanel

        self.panel = FractalParamsPanel()
        self.panel.show()

    def test_formula_changes_toggle_visibility(self) -> None:
        emitted: list[str] = []
        self.panel.formula_changed.connect(emitted.append)

        self.assertEqual(self.panel._formula_combo.itemText(0), "Standard  (z² + c)")
        self.assertEqual(self.panel._formula_combo.itemText(1), "Multibrot  (zⁿ + c)")

        self.panel._on_formula_changed(1)
        self.assertEqual(emitted[-1], "multibrot")
        self.assertTrue(self.panel._power_label.isVisible())
        self.assertTrue(self.panel._power_spin.isVisible())

        self.panel._on_formula_changed(6)
        self.assertEqual(emitted[-1], "phoenix")
        self.assertTrue(self.panel._phoenix_real_spin.isVisible())

        self.panel._on_formula_changed(7)
        self.assertEqual(emitted[-1], "newton")
        self.assertFalse(self.panel._mode_combo.isVisible())
        self.assertTrue(self.panel._power_spin.isVisible())
        self.assertEqual(self.panel._power_label.text(), "Degree (n):")

    def test_mode_and_coloring_transitions_emit_state(self) -> None:
        modes: list[bool] = []
        coloring: list[str] = []
        traps: list[tuple[float, float]] = []

        self.panel.mode_changed.connect(modes.append)
        self.panel.coloring_mode_changed.connect(coloring.append)
        self.panel.trap_point_changed.connect(lambda x, y: traps.append((x, y)))

        self.panel._on_mode_changed("Julia")
        self.panel._on_coloring_changed(3)
        self.panel._trap_x_spin.setValue(0.25)
        self.panel._trap_y_spin.setValue(-0.5)

        self.assertEqual(modes[-1], True)
        self.assertEqual(coloring[-1], "orbit_trap_point")
        self.assertEqual(traps[-1], (0.25, -0.5))
        self.assertTrue(self.panel._julia_real_spin.isVisible())
        self.assertTrue(self.panel._trap_x_spin.isVisible())

    def test_reset_restores_defaults_and_cycle_off(self) -> None:
        cycles: list[bool] = []
        self.panel.cycle_toggled.connect(cycles.append)

        self.panel._cycle_button.setChecked(True)
        self.panel._formula_combo.setCurrentIndex(5)
        self.panel._mode_combo.setCurrentIndex(1)
        self.panel._coloring_combo.setCurrentIndex(3)
        self.panel.reset()

        self.assertFalse(self.panel._cycle_button.isChecked())
        self.assertEqual(self.panel._formula_combo.currentIndex(), 0)
        self.assertEqual(self.panel._mode_combo.currentIndex(), 0)
        self.assertEqual(self.panel._coloring_combo.currentIndex(), 0)
        self.assertGreaterEqual(len(cycles), 1)

    def test_set_scale_updates_zoom_spin_without_exploding(self) -> None:
        self.panel.set_scale(0.03)
        self.assertGreater(self.panel._zoom_spin.value(), 0.0)


class TestThumbnailHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def test_encode_decode_round_trip(self) -> None:
        from fractal_studio.main_window import MainWindow
        from PySide6.QtGui import QColor, QPixmap

        original = QPixmap(96, 72)
        original.fill(QColor("#ff0000"))
        b64 = MainWindow._encode_pixmap(original)
        result = MainWindow._decode_thumbnail(b64)
        self.assertEqual(result.width(), 96)
        self.assertEqual(result.height(), 72)
        self.assertFalse(result.isNull())

    def test_placeholder_pixmap_correct_size(self) -> None:
        from fractal_studio.main_window import MainWindow

        p = MainWindow._placeholder_pixmap()
        self.assertEqual(p.width(), 48)
        self.assertEqual(p.height(), 36)
        self.assertFalse(p.isNull())

    def test_encode_pixmap_returns_valid_base64(self) -> None:
        from fractal_studio.main_window import MainWindow
        from PySide6.QtGui import QColor, QPixmap
        import base64

        pixmap = QPixmap(200, 150)
        pixmap.fill(QColor("#00ff00"))
        b64 = MainWindow._encode_pixmap(pixmap)
        decoded = base64.b64decode(b64)
        self.assertGreater(len(decoded), 0)
        self.assertTrue(decoded[:4] == b"\x89PNG")


class TestPalettePreviewWidget(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def test_paint_event_handles_empty_palette(self) -> None:
        from fractal_studio.editor import PalettePreviewWidget

        widget = PalettePreviewWidget("Preview")
        widget.resize(160, 100)
        widget.paintEvent(QPaintEvent(widget.rect()))

    def test_paint_event_draws_non_empty_palette(self) -> None:
        from fractal_studio.editor import PalettePreviewWidget

        widget = PalettePreviewWidget("Preview")
        widget.resize(160, 100)
        widget.set_palette([(0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0)])
        widget.paintEvent(QPaintEvent(widget.rect()))


class TestColorCubeEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def _make_editor(self, backend=None):
        from fractal_studio.editor import ColorCubeEditor
        from fractal_studio.backend import default_profile

        editor = ColorCubeEditor(backend or DummyEditorBackend(), default_profile())
        editor.resize(540, 540)
        editor.show()
        return editor

    def _point(self, point) -> tuple[int, int]:
        return (round(point.x()), round(point.y()))

    def _click(self, editor, point) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        QTest.mouseClick(editor, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)

    def _press(self, editor, point) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        QTest.mousePress(editor, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)

    def _move(self, editor, point) -> None:
        from PySide6.QtTest import QTest

        QTest.mouseMove(editor, point)

    def _release(self, editor, point) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        QTest.mouseRelease(editor, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)

    def test_seed_clear_and_palette_refresh(self) -> None:
        editor = self._make_editor()
        changed: list[list[tuple[int, int, int]]] = []
        editor.palette_changed.connect(changed.append)

        editor.seed_points()
        self.assertGreaterEqual(len(editor.control_points), 4)
        editor.clear_points()
        self.assertEqual(editor.control_points, [])
        self.assertEqual(changed[-1], [])

    def test_face_pixmap_cache_reuses_same_entry(self) -> None:
        from PySide6.QtCore import QSize

        editor = self._make_editor()
        pixmap_a = editor._face_pixmap(1, QSize(12, 12))
        pixmap_b = editor._face_pixmap(1, QSize(12, 12))
        self.assertIs(pixmap_a, pixmap_b)

    def test_nearest_point_and_projection_threshold(self) -> None:
        from PySide6.QtCore import QPointF

        editor = self._make_editor()
        editor.set_control_points([(10, 10, 10)])
        projected = editor._projected_point(2, editor.control_points[0])
        self.assertEqual(editor._nearest_point(2, QPointF(projected.x(), projected.y())), 0)
        self.assertIsNone(editor._nearest_point(2, QPointF(projected.x() + 200, projected.y() + 200)))

    def test_mouse_press_drag_and_move_updates_point(self) -> None:
        from PySide6.QtCore import QPoint

        editor = self._make_editor()
        editor.set_control_points([(10, 10, 10)])
        projected = editor._projected_point(2, editor.control_points[0])

        start = QPoint(*self._point(projected))
        end = QPoint(start.x() + 8, start.y() + 8)
        self._press(editor, start)
        self.assertIsNotNone(editor._drag_state)
        self._move(editor, end)
        self.assertNotEqual(editor.control_points[0], (10, 10, 10))
        self._release(editor, end)
        self.assertIsNone(editor._drag_state)

    def test_mouse_press_adds_point_and_hover_status(self) -> None:
        from PySide6.QtCore import QPoint

        editor = self._make_editor()

        rect = editor._face_rects()[2]
        pos = QPoint(round(rect.center().x()), round(rect.center().y()))
        self._click(editor, pos)
        self.assertEqual(len(editor.control_points), 1)

    def test_paint_event_handles_backend_missing(self) -> None:
        editor = self._make_editor(backend=DummyUnavailableBackend())
        editor.paintEvent(QPaintEvent(editor.rect()))


class TestViewportSizing(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def test_viewport_prefers_square_shape(self) -> None:
        from fractal_studio.backend import load_backend
        from fractal_studio.viewport import FractalViewportWidget
        from PySide6.QtWidgets import QSizePolicy

        viewport = FractalViewportWidget(load_backend())
        self.assertTrue(viewport.hasHeightForWidth())
        self.assertEqual(viewport.heightForWidth(640), 640)
        self.assertEqual(viewport.sizeHint().width(), viewport.sizeHint().height())
        self.assertEqual(viewport.sizePolicy().verticalPolicy(), QSizePolicy.Policy.Fixed)

    def test_viewport_height_follows_aspect_ratio_mode(self) -> None:
        from fractal_studio.backend import load_backend
        from fractal_studio.viewport import FractalViewportWidget

        viewport = FractalViewportWidget(load_backend())
        scenarios = {"portrait": 800, "landscape": 450}
        for mode, expected in scenarios.items():
            with self.subTest(mode=mode):
                viewport.set_aspect_ratio_mode(mode)
                self.assertEqual(viewport.heightForWidth(600), expected)


class TestViewportHints(QtWindowTestCase):
    def test_hint_mentions_double_click_recenter(self) -> None:
        w = self.make_window()
        self.assertIsNotNone(w.viewport_hint_label)
        self.assertIn("double-click", w.viewport_hint_label.text().lower())
        self.assertIn("recenter", w.viewport_hint_label.text().lower())


class TestWorkspaceLayout(QtWindowTestCase):
    def test_viewport_default_min_width_matches_preview_column(self) -> None:
        w = self.make_window()
        self.assertIsNotNone(w.viewport)
        self.assertEqual(w.viewport.minimumWidth(), 520)


class TestFavoriteThumbnailRow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def _favorite(self, **overrides):
        fav = {
            "name": "Test Fractal",
            "formula": "Mandelbrot",
            "center_x": -0.75,
            "center_y": 0.1,
            "scale": 0.003,
            "max_iterations": 256,
            "is_julia": False,
            "julia_real": 0.0,
            "julia_imag": 0.0,
            "power": 2,
            "phoenix_real": 0.0,
            "phoenix_imag": 0.0,
            "coloring_mode": "smooth",
            "trap_x": 0.0,
            "trap_y": 0.0,
        }
        fav.update(overrides)
        return fav

    def _make_row(self, fav=None):
        from fractal_studio.main_window import FavoriteThumbnailRow
        from PySide6.QtGui import QColor, QPixmap
        from PySide6.QtWidgets import QLabel

        pixmap = QPixmap(48, 36)
        pixmap.fill(QColor("#ff0000"))
        hover_panel = QLabel()
        selected: list[FavoriteThumbnailRow] = []
        activated: list[FavoriteThumbnailRow] = []
        row = FavoriteThumbnailRow(
            pixmap,
            fav or self._favorite(),
            hover_panel,
            lambda r: selected.append(r),
            lambda r: activated.append(r),
        )
        return row, hover_panel, selected, activated

    def test_row_is_not_selected_by_default(self) -> None:
        row, _, _, _ = self._make_row()
        self.assertFalse(row._selected)

    def test_set_selected_changes_stylesheet(self) -> None:
        row, _, _, _ = self._make_row()
        row.set_selected(True)
        self.assertTrue(row._selected)
        self.assertIn("#2f6feb", row.styleSheet())
        row.set_selected(False)
        self.assertFalse(row._selected)

    def test_hover_state_changes_stylesheet(self) -> None:
        row, _, _, _ = self._make_row()
        row._set_hovered(True)
        self.assertIn("#94a3b8", row.styleSheet())
        row._set_hovered(False)
        self.assertIn("transparent", row.styleSheet())

    def test_click_calls_on_select(self) -> None:
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        row, _, selected, _ = self._make_row()
        row.show()
        QTest.mouseClick(row, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(10, 10))
        self.assertEqual(len(selected), 1)
        self.assertIs(selected[0], row)

    def test_double_click_calls_activate(self) -> None:
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        row, _, _, activated = self._make_row()
        row.show()
        QTest.mouseDClick(row, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(10, 10))
        self.assertEqual(len(activated), 1)
        self.assertIs(activated[0], row)

    def test_stats_html_contains_formula(self) -> None:
        row, _, _, _ = self._make_row()
        html = row._build_stats_html()
        self.assertIn("Mandelbrot", html)
        self.assertIn("-0.750000", html)

    def test_stats_html_includes_optional_fields(self) -> None:
        from fractal_studio.main_window import FavoriteThumbnailRow
        from PySide6.QtGui import QColor, QPixmap
        from PySide6.QtWidgets import QLabel

        pixmap = QPixmap(48, 36)
        pixmap.fill(QColor("#ff0000"))
        scenarios = [
            ("Julia", self._favorite(is_julia=True, julia_real=-0.8, julia_imag=0.156), "Julia c"),
            ("Phoenix", self._favorite(formula="Phoenix", phoenix_real=0.5, phoenix_imag=0.25), "Phoenix"),
            ("Orbit trap", self._favorite(coloring_mode="orbit_trap_point", trap_x=0.5, trap_y=-0.25), "Trap pt"),
        ]

        for label, fav, expected in scenarios:
            with self.subTest(label=label):
                row = FavoriteThumbnailRow(pixmap, fav, QLabel(), lambda _: None)
                self.assertIn(expected, row._build_stats_html())


class TestFavoritePersistence(QtWindowTestCase):
    def setUp(self) -> None:
        import fractal_studio.main_window as mwmod

        self._mwmod = mwmod
        self._original_path = mwmod._FAVORITES_PATH
        self._tmpdir = Path(tempfile.mkdtemp(prefix="fs_test_favs_"))
        mwmod._FAVORITES_PATH = self._tmpdir / "favorites.json"

    def tearDown(self) -> None:
        self._mwmod._FAVORITES_PATH = self._original_path

    def test_load_favorite_restores_control_points(self) -> None:
        w = self.make_window()
        self.assertIsNotNone(w.editor)

        initial_points = [(12, 34, 56), (78, 90, 123), (140, 150, 160), (200, 210, 220)]
        replacement_points = [(1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12)]

        w.editor.set_control_points(initial_points)
        w._save_favorite()
        w.editor.set_control_points(replacement_points)

        row = w._fav_rows[-1]
        w._on_row_selected(row)
        w._load_favorite()

        self.assertEqual(w.editor.control_points, initial_points)

    def test_load_favorite_restores_aspect_ratio_mode(self) -> None:
        w = self.make_window()
        self.assertIsNotNone(w._aspect_ratio_combo)

        w._aspect_ratio_combo.setCurrentIndex(1)
        w._save_favorite()
        self.assertEqual(w._favorites[-1]["aspect_ratio_mode"], "portrait")

        w._aspect_ratio_combo.setCurrentIndex(2)
        row = w._fav_rows[-1]
        w._on_row_selected(row)
        w._load_favorite()

        self.assertEqual(w._aspect_ratio_combo.currentIndex(), 1)
        self.assertEqual(w.viewport.aspect_ratio_mode(), "portrait")
        self.assertIn("1080 × 1440", w._export_combo.itemText(0))

    def test_save_after_load_appends_and_preserves_original(self) -> None:
        w = self.make_window()
        self.assertIsNotNone(w.viewport)

        w._save_favorite()
        self.assertEqual(len(w._favorites), 1)
        original = dict(w._favorites[0])

        row = w._fav_rows[0]
        w._on_row_selected(row)
        w._load_favorite()
        w.viewport._center_x += 0.5
        w._save_favorite()

        self.assertEqual(len(w._favorites), 2)
        self.assertEqual(w._favorites[0]["center_x"], original["center_x"])
        self.assertNotEqual(w._favorites[1]["center_x"], w._favorites[0]["center_x"])
        self.assertRegex(w._favorites[0]["name"], r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
        self.assertRegex(w._favorites[1]["name"], r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
        self.assertNotEqual(w._favorites[0]["name"], w._favorites[1]["name"])
        self.assertIn("id", w._favorites[0])
        self.assertIn("id", w._favorites[1])
        self.assertNotEqual(w._favorites[0]["id"], w._favorites[1]["id"])

    def test_load_restores_saved_palette_instead_of_current_palette(self) -> None:
        w = self.make_window()
        self.assertIsNotNone(w.viewport)
        self.assertIsNotNone(w.editor)

        original_points = [(20, 30, 40), (60, 80, 100), (120, 140, 160), (200, 220, 240)]
        different_points = [(5, 10, 15), (25, 35, 45), (85, 95, 105), (145, 155, 165)]

        w.editor.set_control_points(original_points)
        expected_palette = list(w.viewport._palette)
        w._save_favorite()

        w.editor.set_control_points(different_points)
        self.assertNotEqual(list(w.viewport._palette), expected_palette)

        row = w._fav_rows[-1]
        w._on_row_selected(row)
        w._load_favorite()

        self.assertEqual(list(w.viewport._palette), expected_palette)

    def test_load_favorites_from_disk_returns_empty_for_missing_or_corrupt_file(self) -> None:
        w = self.make_window()
        self.assertEqual(w._load_favorites_from_disk(), [])
        self._mwmod._FAVORITES_PATH.write_text("not json")
        self.assertEqual(w._load_favorites_from_disk(), [])


if __name__ == "__main__":
    unittest.main()
