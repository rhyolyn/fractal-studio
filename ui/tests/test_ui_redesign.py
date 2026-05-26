from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from PySide6.QtWidgets import QApplication

_APP: QApplication | None = None


def _get_app() -> QApplication:
    global _APP
    if QApplication.instance() is None:
        _APP = QApplication([])
    return QApplication.instance()


class TestCustomResolutionDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def test_default_values(self) -> None:
        from fractal_studio.main_window import CustomResolutionDialog
        dlg = CustomResolutionDialog(1920, 1080)
        w, h = dlg.values()
        self.assertEqual(w, 1920)
        self.assertEqual(h, 1080)

    def test_custom_values(self) -> None:
        from fractal_studio.main_window import CustomResolutionDialog
        dlg = CustomResolutionDialog(3840, 2160)
        w, h = dlg.values()
        self.assertEqual(w, 3840)
        self.assertEqual(h, 2160)

    def test_spinbox_range(self) -> None:
        from fractal_studio.main_window import CustomResolutionDialog
        dlg = CustomResolutionDialog(1920, 1080)
        # Attempt values below minimum — Qt should clamp to 64
        dlg._width_box.setValue(0)
        dlg._height_box.setValue(-1)
        w, h = dlg.values()
        self.assertEqual(w, 64)
        self.assertEqual(h, 64)
        # Attempt values above maximum — Qt should clamp to 16384
        dlg._width_box.setValue(99999)
        dlg._height_box.setValue(99999)
        w, h = dlg.values()
        self.assertEqual(w, 16384)
        self.assertEqual(h, 16384)


class TestExportPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def _make_window(self):
        from fractal_studio.main_window import MainWindow
        return MainWindow()

    def test_export_combo_has_five_items(self) -> None:
        w = self._make_window()
        self.assertEqual(w._export_combo.count(), 4)
        w.close()

    def test_export_combo_last_item_is_custom(self) -> None:
        w = self._make_window()
        last = w._export_combo.itemText(3)
        self.assertIn("Custom", last)
        w.close()

    def test_export_combo_default_is_1080_square(self) -> None:
        w = self._make_window()
        self.assertEqual(w._export_combo.currentIndex(), 0)
        self.assertIn("1080 × 1080", w._export_combo.itemText(0))
        w.close()

    def test_aspect_ratio_combo_has_three_modes(self) -> None:
        w = self._make_window()
        self.assertEqual(w._aspect_ratio_combo.count(), 3)
        self.assertEqual(w._aspect_ratio_combo.currentIndex(), 0)
        self.assertIn("(1:1)", w._aspect_ratio_combo.itemText(0))
        self.assertIn("(3:4)", w._aspect_ratio_combo.itemText(1))
        self.assertIn("(4:3)", w._aspect_ratio_combo.itemText(2))
        w.close()

    def test_export_presets_follow_square_portrait_landscape(self) -> None:
        w = self._make_window()

        self.assertIn("1080 × 1080", w._export_combo.itemText(0))

        w._aspect_ratio_combo.setCurrentIndex(1)
        self.assertIn("1080 × 1440", w._export_combo.itemText(0))

        w._aspect_ratio_combo.setCurrentIndex(2)
        self.assertIn("1440 × 1080", w._export_combo.itemText(0))

        w.close()

    def test_custom_size_row_hidden_by_default(self) -> None:
        w = self._make_window()
        self.assertTrue(w._custom_width_box.parentWidget().isHidden())
        w.close()

    def test_custom_size_row_shown_for_custom_preset(self) -> None:
        w = self._make_window()
        w._export_combo.setCurrentIndex(3)
        self.assertFalse(w._custom_width_box.parentWidget().isHidden())
        w.close()

    def test_export_uses_inline_custom_dimensions(self) -> None:
        from fractal_studio.main_window import MainWindow
        captured = []
        original = MainWindow._export_render
        try:
            MainWindow._export_render = lambda self, width, height: captured.append((width, height))
            w = self._make_window()
            w._export_combo.setCurrentIndex(3)
            w._custom_width_box.setValue(1234)
            w._custom_height_box.setValue(567)
            w._on_export_clicked()
            self.assertEqual(captured, [(1234, 567)])
            w.close()
        finally:
            MainWindow._export_render = original


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
        import base64
        from PySide6.QtGui import QColor, QPixmap
        pixmap = QPixmap(200, 150)
        pixmap.fill(QColor("#00ff00"))
        b64 = MainWindow._encode_pixmap(pixmap)
        decoded = base64.b64decode(b64)
        self.assertGreater(len(decoded), 0)
        # PNG magic bytes
        self.assertTrue(decoded[:4] == b'\x89PNG')


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
        viewport.set_aspect_ratio_mode("portrait")
        self.assertEqual(viewport.heightForWidth(600), 800)
        viewport.set_aspect_ratio_mode("landscape")
        self.assertEqual(viewport.heightForWidth(600), 450)


class TestViewportHints(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def test_hint_mentions_double_click_recenter(self) -> None:
        from fractal_studio.main_window import MainWindow

        w = MainWindow()
        self.assertIsNotNone(w.viewport_hint_label)
        self.assertIn("double-click", w.viewport_hint_label.text().lower())
        self.assertIn("recenter", w.viewport_hint_label.text().lower())
        w.close()


class TestWorkspaceLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def test_viewport_default_min_width_matches_preview_column(self) -> None:
        from fractal_studio.main_window import MainWindow

        w = MainWindow()
        self.assertIsNotNone(w.viewport)
        self.assertEqual(w.viewport.minimumWidth(), 520)
        w.close()


class TestFavoriteThumbnailRow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def _make_row(self, name="Test Fractal"):
        from fractal_studio.main_window import FavoriteThumbnailRow
        from PySide6.QtGui import QColor, QPixmap
        from PySide6.QtWidgets import QLabel
        pixmap = QPixmap(48, 36)
        pixmap.fill(QColor("#ff0000"))
        hover_panel = QLabel()
        fav = {
            "name": name,
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
        selected = []
        activated = []
        row = FavoriteThumbnailRow(
            pixmap,
            fav,
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
        from PySide6.QtCore import QPoint
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        row, _, selected, _ = self._make_row()
        row.show()
        QTest.mouseClick(row, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(10, 10))
        self.assertEqual(len(selected), 1)
        self.assertIs(selected[0], row)
        row.close()

    def test_double_click_calls_activate(self) -> None:
        from PySide6.QtCore import QPoint
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        row, _, _, activated = self._make_row()
        row.show()
        QTest.mouseDClick(row, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(10, 10))
        self.assertEqual(len(activated), 1)
        self.assertIs(activated[0], row)
        row.close()

    def test_stats_html_contains_formula(self) -> None:
        row, _, _, _ = self._make_row()
        html = row._build_stats_html()
        self.assertIn("Mandelbrot", html)
        self.assertIn("-0.750000", html)


class TestFavoritePersistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def setUp(self) -> None:
        import fractal_studio.main_window as mwmod
        self._mwmod = mwmod
        self._original_path = mwmod._FAVORITES_PATH
        self._tmpdir = Path(tempfile.mkdtemp(prefix="fs_test_favs_"))
        mwmod._FAVORITES_PATH = self._tmpdir / "favorites.json"

    def tearDown(self) -> None:
        self._mwmod._FAVORITES_PATH = self._original_path

    def test_load_favorite_restores_control_points(self) -> None:
        from fractal_studio.main_window import MainWindow
        w = MainWindow()
        self.assertIsNotNone(w.editor)

        initial_points = [
            (12, 34, 56),
            (78, 90, 123),
            (140, 150, 160),
            (200, 210, 220),
        ]
        replacement_points = [
            (1, 2, 3),
            (4, 5, 6),
            (7, 8, 9),
            (10, 11, 12),
        ]

        w.editor.set_control_points(initial_points)
        w._save_favorite()
        w.editor.set_control_points(replacement_points)

        row = w._fav_rows[-1]
        w._on_row_selected(row)
        w._load_favorite()

        self.assertEqual(w.editor.control_points, initial_points)
        w.close()

    def test_load_favorite_restores_aspect_ratio_mode(self) -> None:
        from fractal_studio.main_window import MainWindow
        w = MainWindow()
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
        w.close()

    def test_save_after_load_appends_and_preserves_original(self) -> None:
        from fractal_studio.main_window import MainWindow
        w = MainWindow()
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
        w.close()

    def test_load_restores_saved_palette_instead_of_current_palette(self) -> None:
        from fractal_studio.main_window import MainWindow
        w = MainWindow()
        self.assertIsNotNone(w.viewport)
        self.assertIsNotNone(w.editor)

        original_points = [
            (20, 30, 40),
            (60, 80, 100),
            (120, 140, 160),
            (200, 220, 240),
        ]
        different_points = [
            (5, 10, 15),
            (25, 35, 45),
            (85, 95, 105),
            (145, 155, 165),
        ]

        w.editor.set_control_points(original_points)
        expected_palette = list(w.viewport._palette)
        w._save_favorite()

        w.editor.set_control_points(different_points)
        self.assertNotEqual(list(w.viewport._palette), expected_palette)

        row = w._fav_rows[-1]
        w._on_row_selected(row)
        w._load_favorite()

        self.assertEqual(list(w.viewport._palette), expected_palette)
        w.close()


if __name__ == "__main__":
    unittest.main()
