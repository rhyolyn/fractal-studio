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
class TestFavoriteHoverPresenter(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_app()

    def _favorite(self, **overrides):
        favorite = {
            "name": "Sample",
            "formula": "Mandelbrot",
            "center_x": -0.75,
            "center_y": 0.1,
            "scale": 0.003,
            "max_iterations": 256,
            "is_julia": False,
            "power": 2,
            "formula_params": {"type": "standard"},
            "coloring_mode": "smooth",
        }
        favorite.update(overrides)
        return favorite

    def test_build_stats_html_contains_core_values(self) -> None:
        from fractal_studio.ui.presenters.favorite_hover_presenter import (
            FavoriteHoverPresenter,
        )
        from PySide6.QtWidgets import QWidget

        presenter = FavoriteHoverPresenter()
        row = QWidget()

        html = presenter.build_stats_html(row, self._favorite())

        self.assertIn("Mandelbrot", html)
        self.assertIn("-0.750000", html)
        self.assertIn("Iterations", html)

    def test_hide_hides_hover_panel(self) -> None:
        from fractal_studio.ui.presenters.favorite_hover_presenter import (
            FavoriteHoverPresenter,
        )
        from PySide6.QtWidgets import QLabel

        presenter = FavoriteHoverPresenter()
        panel = QLabel("hover")
        panel.show()

        presenter.hide(panel)

        self.assertFalse(panel.isVisible())


@pytest.mark.integration
class TestFavoriteThumbnailRow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_app()

    def _favorite(self, **overrides):
        fav = {
            "name": "Test Fractal",
            "formula": "Mandelbrot",
            "center_x": -0.75,
            "center_y": 0.1,
            "scale": 0.003,
            "max_iterations": 256,
            "is_julia": False,
            "power": 2,
            "formula_params": {"type": "standard"},
            "coloring_mode": "smooth",
        }
        fav.update(overrides)
        return fav

    def _make_row(self, fav=None):
        from fractal_studio.ui.widgets.favorite_thumbnail_row import (
            FavoriteThumbnailRow,
        )
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

    def _enter_row(self, row) -> None:
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QEnterEvent
        from PySide6.QtWidgets import QApplication

        row.show()
        enter_event = QEnterEvent(QPointF(10, 10), QPointF(10, 10), QPointF(10, 10))
        QApplication.sendEvent(row, enter_event)
        QApplication.processEvents()

    def _leave_row(self, row) -> None:
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QApplication

        QApplication.sendEvent(row, QEvent(QEvent.Type.Leave))
        QApplication.processEvents()

    def test_row_is_not_selected_by_default(self) -> None:
        row, _, _, _ = self._make_row()
        self.assertIn("transparent", row.styleSheet())

    def test_set_selected_changes_stylesheet(self) -> None:
        from fractal_studio.theme import get_theme

        row, _, _, _ = self._make_row()
        row.set_selected(True)
        self.assertIn(get_theme("light").selected_border, row.styleSheet())
        row.set_selected(False)
        self.assertIn("transparent", row.styleSheet())

    def test_hover_state_changes_stylesheet(self) -> None:
        from fractal_studio.theme import get_theme

        row, hover_panel, _, _ = self._make_row()
        self._enter_row(row)
        self.assertIn(get_theme("light").hover_border, row.styleSheet())
        self.assertTrue(hover_panel.isVisible())
        self._leave_row(row)
        self.assertIn("transparent", row.styleSheet())

    def test_click_calls_on_select(self) -> None:
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        row, _, selected, _ = self._make_row()
        row.show()
        QTest.mouseClick(
            row,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(10, 10),
        )
        self.assertEqual(len(selected), 1)
        self.assertIs(selected[0], row)

    def test_double_click_calls_activate(self) -> None:
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        row, _, _, activated = self._make_row()
        row.show()
        QTest.mouseDClick(
            row,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(10, 10),
        )
        self.assertEqual(len(activated), 1)
        self.assertIs(activated[0], row)

    def test_stats_html_contains_formula(self) -> None:
        row, hover_panel, _, _ = self._make_row()
        self._enter_row(row)
        self.assertIn("Mandelbrot", hover_panel.text())
        self.assertIn("-0.750000", hover_panel.text())

    def test_stats_html_includes_optional_fields(self) -> None:
        from fractal_studio.ui.widgets.favorite_thumbnail_row import (
            FavoriteThumbnailRow,
        )
        from PySide6.QtGui import QColor, QPixmap
        from PySide6.QtWidgets import QLabel

        pixmap = QPixmap(48, 36)
        pixmap.fill(QColor("#ff0000"))
        scenarios = [
            (
                "Julia",
                self._favorite(is_julia=True, formula_params={"type": "julia", "cx": -0.8, "cy": 0.156}),
                "Julia c",
            ),
            (
                "Phoenix",
                self._favorite(formula="Phoenix", formula_params={"type": "phoenix", "real": 0.5, "imag": 0.25}),
                "Phoenix",
            ),
            (
                "Orbit trap",
                self._favorite(
                    coloring_mode="orbit_trap_point",
                    formula_params={"type": "newton", "trap_x": 0.5, "trap_y": -0.25},
                ),
                "Trap pt",
            ),
        ]

        for label, fav, expected in scenarios:
            with self.subTest(label=label):
                hover_panel = QLabel()
                row = FavoriteThumbnailRow(pixmap, fav, hover_panel, lambda _: None)
                self._enter_row(row)
                self.assertIn(expected, hover_panel.text())


@pytest.mark.integration
class TestFavoriteRowStylePresenter(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_app()

    def test_apply_visual_state_selected(self) -> None:
        from fractal_studio.ui.presenters.favorite_row_style_presenter import (
            FavoriteRowStylePresenter,
        )
        from fractal_studio.theme import get_theme
        from PySide6.QtWidgets import QLabel, QWidget

        presenter = FavoriteRowStylePresenter()
        row = QWidget()
        thumb = QLabel()
        name = QLabel()

        presenter.apply_visual_state(row, thumb, name, selected=True, hovered=False)

        theme = get_theme("light")
        self.assertIn(theme.selected_border, row.styleSheet())
        self.assertIn(theme.selected_border, thumb.styleSheet())
        self.assertIn("font-weight: 600", name.styleSheet())

    def test_apply_visual_state_hovered(self) -> None:
        from fractal_studio.ui.presenters.favorite_row_style_presenter import (
            FavoriteRowStylePresenter,
        )
        from fractal_studio.theme import get_theme
        from PySide6.QtWidgets import QLabel, QWidget

        presenter = FavoriteRowStylePresenter()
        row = QWidget()
        thumb = QLabel()
        name = QLabel()

        presenter.apply_visual_state(row, thumb, name, selected=False, hovered=True)

        theme = get_theme("light")
        self.assertIn(theme.hover_border, row.styleSheet())
        self.assertIn(theme.hover_border, thumb.styleSheet())
        self.assertEqual(name.styleSheet(), "")

    def test_apply_visual_state_default(self) -> None:
        from fractal_studio.ui.presenters.favorite_row_style_presenter import (
            FavoriteRowStylePresenter,
        )
        from PySide6.QtWidgets import QLabel, QWidget

        presenter = FavoriteRowStylePresenter()
        row = QWidget()
        thumb = QLabel()
        name = QLabel()

        presenter.apply_visual_state(row, thumb, name, selected=False, hovered=False)

        self.assertIn("transparent", row.styleSheet())
        self.assertIn("transparent", thumb.styleSheet())
        self.assertEqual(name.styleSheet(), "")


@pytest.mark.integration
class TestFavoritePersistence(QtWindowTestCase):
    def _activate_row(self, window, index: int = -1) -> None:
        from fractal_studio.ui.widgets.favorite_thumbnail_row import (
            FavoriteThumbnailRow,
        )
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        window.show()
        get_app().processEvents()
        rows = window.findChildren(FavoriteThumbnailRow)
        self.assertGreater(len(rows), 0)
        row = rows[index]
        row.show()
        QTest.mouseDClick(
            row,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(10, 10),
        )

    def _save_favorite_via_ui(self, window) -> None:
        from PySide6.QtWidgets import QPushButton

        window.show()
        get_app().processEvents()
        save_buttons = [
            button
            for button in window.findChildren(QPushButton)
            if button.text() == "Save"
        ]
        self.assertEqual(len(save_buttons), 1)
        save_buttons[0].click()
        get_app().processEvents()

    def _delete_favorite_via_ui(self, window) -> None:
        from PySide6.QtWidgets import QPushButton

        window.show()
        get_app().processEvents()
        delete_buttons = [
            button
            for button in window.findChildren(QPushButton)
            if button.text() == "Delete"
        ]
        self.assertEqual(len(delete_buttons), 1)
        delete_buttons[0].click()
        get_app().processEvents()

    def _find_aspect_combo(self, window) -> QComboBox:
        for combo in window.findChildren(QComboBox):
            labels = [combo.itemText(i) for i in range(combo.count())]
            if labels[:3] == ["Square (1:1)", "Portrait (3:4)", "Landscape (4:3)"]:
                return combo
        raise AssertionError("Aspect ratio combo not found")

    def _find_export_combo(self, window) -> QComboBox:
        for combo in window.findChildren(QComboBox):
            labels = [combo.itemText(i) for i in range(combo.count())]
            if any("Custom" in label for label in labels):
                return combo
        raise AssertionError("Export combo not found")

    def setUp(self) -> None:
        import fractal_studio.main_window_factory as mwmod

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
        self._save_favorite_via_ui(w)
        w.editor.set_control_points(replacement_points)

        self._activate_row(w)

        self.assertEqual(w.editor.control_points, initial_points)

    def test_main_window_sections_state_hides_colormap_widget_aliases(self) -> None:
        w = self.make_window()

        self.assertIsNotNone(w.editor)
        with self.assertRaises(AttributeError):
            _ = w._sections_state.editor

    def test_load_favorite_restores_aspect_ratio_mode(self) -> None:
        w = self.make_window()
        aspect_combo = self._find_aspect_combo(w)
        export_combo = self._find_export_combo(w)

        aspect_combo.setCurrentIndex(1)
        self._save_favorite_via_ui(w)

        aspect_combo.setCurrentIndex(2)
        self._activate_row(w)

        self.assertEqual(aspect_combo.currentIndex(), 1)
        self.assertEqual(w.viewport.aspect_ratio_mode(), "portrait")
        self.assertIn("1080 × 1440", export_combo.itemText(0))

    def test_save_after_load_appends_and_preserves_original(self) -> None:
        w = self.make_window()
        self.assertIsNotNone(w.viewport)
        from fractal_studio.ui.widgets.favorite_thumbnail_row import (
            FavoriteThumbnailRow,
        )

        self._save_favorite_via_ui(w)
        self.assertEqual(len(w.findChildren(FavoriteThumbnailRow)), 1)

        self._activate_row(w, 0)
        original_center_x = w.viewport.to_state().center_x
        current_state = w.viewport.to_state()
        w.viewport.apply_state(
            replace(current_state, center_x=current_state.center_x + 0.5)
        )
        modified_center_x = w.viewport.to_state().center_x
        self._save_favorite_via_ui(w)

        self.assertEqual(len(w.findChildren(FavoriteThumbnailRow)), 2)

        self._activate_row(w, 0)
        first_center_x = w.viewport.to_state().center_x

        self._activate_row(w, -1)
        second_center_x = w.viewport.to_state().center_x

        self.assertAlmostEqual(first_center_x, original_center_x, places=6)
        self.assertAlmostEqual(second_center_x, modified_center_x, places=6)
        self.assertNotAlmostEqual(first_center_x, second_center_x, places=6)

    def test_load_restores_saved_palette_instead_of_current_palette(self) -> None:
        w = self.make_window()
        self.assertIsNotNone(w.viewport)
        self.assertIsNotNone(w.editor)

        original_points = [
            (20, 30, 40),
            (60, 80, 100),
            (120, 140, 160),
            (200, 220, 240),
        ]
        different_points = [(5, 10, 15), (25, 35, 45), (85, 95, 105), (145, 155, 165)]

        w.editor.set_control_points(original_points)
        expected_palette = w.viewport.palette()
        self._save_favorite_via_ui(w)

        w.editor.set_control_points(different_points)
        self.assertNotEqual(w.viewport.palette(), expected_palette)

        self._activate_row(w)

        self.assertEqual(w.viewport.palette(), expected_palette)

    def test_load_favorites_from_disk_returns_empty_for_missing_or_corrupt_file(
        self,
    ) -> None:
        from fractal_studio.persistence import FavoritesRepository

        repo = FavoritesRepository(self._mwmod._FAVORITES_PATH)

        self.assertEqual(repo.load(), [])
        self.assertEqual(repo.last_load_diagnostic, "")
        self._mwmod._FAVORITES_PATH.write_text("not json")
        self.assertEqual(repo.load(), [])
        self.assertIn(
            "ignored invalid favorites file", repo.last_load_diagnostic.lower()
        )

    def test_save_favorite_persists_versioned_payload(self) -> None:
        w = self.make_window()
        self._save_favorite_via_ui(w)

        raw = json.loads(self._mwmod._FAVORITES_PATH.read_text())
        self.assertEqual(raw.get("version"), 1)
        self.assertIsInstance(raw.get("favorites"), list)
        self.assertEqual(len(raw["favorites"]), 1)

    def test_load_favorites_supports_legacy_list_format(self) -> None:
        from fractal_studio.persistence import FavoritesRepository

        w = self.make_window()
        self._save_favorite_via_ui(w)
        raw_payload = json.loads(self._mwmod._FAVORITES_PATH.read_text())
        legacy_entry = dict(raw_payload["favorites"][0])
        self._mwmod._FAVORITES_PATH.write_text(json.dumps([legacy_entry]))

        loaded = FavoritesRepository(self._mwmod._FAVORITES_PATH).load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].to_dict()["id"], legacy_entry["id"])

    def test_load_favorites_supports_versioned_format(self) -> None:
        from fractal_studio.persistence import FavoritesRepository

        w = self.make_window()
        self._save_favorite_via_ui(w)
        raw_payload = json.loads(self._mwmod._FAVORITES_PATH.read_text())
        entry = dict(raw_payload["favorites"][0])
        self._mwmod._FAVORITES_PATH.write_text(
            json.dumps({"version": 1, "favorites": [entry]})
        )

        loaded = FavoritesRepository(self._mwmod._FAVORITES_PATH).load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].to_dict()["name"], entry["name"])

    def test_load_favorites_supports_versioned_format_with_empty_favorites(
        self,
    ) -> None:
        from fractal_studio.persistence import FavoritesRepository

        self._mwmod._FAVORITES_PATH.write_text(
            json.dumps({"version": 1, "favorites": []})
        )

        loaded = FavoritesRepository(self._mwmod._FAVORITES_PATH).load()
        self.assertEqual(len(loaded), 0)

    def test_delete_button_removes_selected_favorite_and_persists(self) -> None:
        from fractal_studio.ui.widgets.favorite_thumbnail_row import (
            FavoriteThumbnailRow,
        )

        w = self.make_window()

        self._save_favorite_via_ui(w)
        self._save_favorite_via_ui(w)
        rows = w.findChildren(FavoriteThumbnailRow)
        self.assertEqual(len(rows), 2)
        w._sections_state.favorites.selected_row = rows[-1]
        self._delete_favorite_via_ui(w)

        self.assertEqual(len(w._sections_state.favorites.fav_rows), 1)
        self.assertIsNone(w._sections_state.favorites.selected_row)
        raw = json.loads(self._mwmod._FAVORITES_PATH.read_text())
        self.assertEqual(raw.get("version"), 1)
        self.assertEqual(len(raw.get("favorites", [])), 1)

    def test_main_window_sections_state_hides_favorites_aliases(self) -> None:
        w = self.make_window()

        with self.assertRaises(AttributeError):
            _ = w._sections_state.selected_row

    def test_delete_button_without_selection_keeps_favorites_unchanged(self) -> None:
        from fractal_studio.ui.widgets.favorite_thumbnail_row import (
            FavoriteThumbnailRow,
        )

        w = self.make_window()

        self._save_favorite_via_ui(w)
        self.assertEqual(len(w.findChildren(FavoriteThumbnailRow)), 1)
        before = json.loads(self._mwmod._FAVORITES_PATH.read_text())

        self._delete_favorite_via_ui(w)

        self.assertEqual(len(w.findChildren(FavoriteThumbnailRow)), 1)
        after = json.loads(self._mwmod._FAVORITES_PATH.read_text())
        self.assertEqual(after, before)


