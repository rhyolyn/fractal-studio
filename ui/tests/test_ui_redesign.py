from __future__ import annotations

import gc
import sys
import tempfile
import unittest
import json
from dataclasses import replace
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QApplication, QComboBox, QSpinBox

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


class DummyPaletteBackend:
    available = True

    def __init__(self) -> None:
        self.saved: list[tuple[str, list[tuple[int, int, int]], int]] = []
        self.loaded_paths: list[str] = []
        self.exported: list[tuple[str, list[tuple[int, int, int]]]] = []

    def export_palette_json(self, path: str, control_points: list[tuple[int, int, int]], palette_size: int) -> None:
        self.saved.append((path, list(control_points), palette_size))

    def import_palette_json(self, path: str) -> tuple[int, list[tuple[int, int, int]]]:
        self.loaded_paths.append(path)
        return 6, [(1, 2, 3), (4, 5, 6)]

    def generate_palette(self, control_points: list[tuple[int, int, int]], palette_size: int) -> list[tuple[int, int, int]]:
        self.exported.append(("generated", list(control_points)))
        return list(control_points[:palette_size])

    def export_legacy_map(self, path: str, palette: list[tuple[int, int, int]]) -> None:
        self.exported.append((path, list(palette)))


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
    def _find_export_combo(self, window) -> QComboBox:
        for combo in window.findChildren(QComboBox):
            labels = [combo.itemText(i) for i in range(combo.count())]
            if any("Custom" in label for label in labels):
                return combo
        raise AssertionError("Export combo not found")

    def _find_aspect_combo(self, window) -> QComboBox:
        for combo in window.findChildren(QComboBox):
            labels = [combo.itemText(i) for i in range(combo.count())]
            if labels[:3] == ["Square (1:1)", "Portrait (3:4)", "Landscape (4:3)"]:
                return combo
        raise AssertionError("Aspect ratio combo not found")

    def _find_export_custom_spinboxes(self, window) -> tuple[QSpinBox, QSpinBox]:
        spinboxes = [
            spinbox
            for spinbox in window.findChildren(QSpinBox)
            if spinbox.minimum() == 64 and spinbox.maximum() == 16384
        ]
        if len(spinboxes) != 2:
            raise AssertionError("Expected exactly two export custom size spinboxes")
        return spinboxes[0], spinboxes[1]

    def test_export_combo_has_four_items(self) -> None:
        w = self.make_window()
        export_combo = self._find_export_combo(w)
        self.assertEqual(export_combo.count(), 4)

    def test_export_combo_last_item_is_custom(self) -> None:
        w = self.make_window()
        export_combo = self._find_export_combo(w)
        self.assertIn("Custom", export_combo.itemText(3))

    def test_export_combo_default_is_square(self) -> None:
        w = self.make_window()
        export_combo = self._find_export_combo(w)
        self.assertEqual(export_combo.currentIndex(), 0)
        self.assertIn("1080 × 1080", export_combo.itemText(0))

    def test_aspect_ratio_combo_has_three_modes(self) -> None:
        w = self.make_window()
        aspect_combo = self._find_aspect_combo(w)
        self.assertEqual(aspect_combo.count(), 3)
        expected_labels = ["(1:1)", "(3:4)", "(4:3)"]
        for index, suffix in enumerate(expected_labels):
            with self.subTest(index=index):
                self.assertIn(suffix, aspect_combo.itemText(index))

    def test_export_presets_follow_aspect_ratio(self) -> None:
        w = self.make_window()
        aspect_combo = self._find_aspect_combo(w)
        export_combo = self._find_export_combo(w)
        scenarios = [
            (0, "1080 × 1080"),
            (1, "1080 × 1440"),
            (2, "1440 × 1080"),
        ]

        for index, expected in scenarios:
            with self.subTest(aspect=index):
                aspect_combo.setCurrentIndex(index)
                self.assertIn(expected, export_combo.itemText(0))

    def test_unknown_aspect_ratio_defaults_to_square_presets(self) -> None:
        from fractal_studio.favorites_controller import FavoritesController
        from fractal_studio.main_window_controller import MainWindowController

        controller = MainWindowController(export_service=object(), favorites_controller=FavoritesController())
        self.assertEqual(
            controller.build_export_presets_for_mode("unexpected")[0],
            ("1080 × 1080", 1080, 1080),
        )

    def test_custom_size_row_hidden_by_default(self) -> None:
        w = self.make_window()
        width_box, _ = self._find_export_custom_spinboxes(w)
        self.assertTrue(width_box.parentWidget().isHidden())

    def test_custom_size_row_shown_for_custom_preset(self) -> None:
        w = self.make_window()
        export_combo = self._find_export_combo(w)
        width_box, _ = self._find_export_custom_spinboxes(w)
        export_combo.setCurrentIndex(3)
        self.assertFalse(width_box.parentWidget().isHidden())


class TestMainWindowController(unittest.TestCase):
    def test_on_export_clicked_uses_custom_dimensions(self) -> None:
        from fractal_studio.favorites_controller import FavoritesController
        from fractal_studio.main_window_controller import MainWindowController

        class Box:
            def __init__(self, value: int) -> None:
                self._value = value

            def value(self) -> int:
                return self._value

        controller = MainWindowController(export_service=object(), favorites_controller=FavoritesController())
        captured: list[tuple[int, int]] = []
        custom_sizes: list[tuple[int, int]] = []

        controller.on_export_clicked(
            export_presets=[("1080 × 1080", 1080, 1080), ("Custom…", 0, 0)],
            index=1,
            custom_width_box=Box(1234),
            custom_height_box=Box(567),
            set_custom_size=lambda w, h: custom_sizes.append((w, h)),
            export_callback=lambda w, h: captured.append((w, h)),
        )

        self.assertEqual(custom_sizes, [(1234, 567)])
        self.assertEqual(captured, [(1234, 567)])

    def test_on_export_clicked_uses_selected_preset_dimensions(self) -> None:
        from fractal_studio.favorites_controller import FavoritesController
        from fractal_studio.main_window_controller import MainWindowController

        controller = MainWindowController(export_service=object(), favorites_controller=FavoritesController())
        captured: list[tuple[int, int]] = []
        custom_sizes: list[tuple[int, int]] = []

        controller.on_export_clicked(
            export_presets=[("1080 × 1080", 1080, 1080), ("Custom…", 0, 0)],
            index=0,
            custom_width_box=None,
            custom_height_box=None,
            set_custom_size=lambda w, h: custom_sizes.append((w, h)),
            export_callback=lambda w, h: captured.append((w, h)),
        )

        self.assertEqual(custom_sizes, [])
        self.assertEqual(captured, [(1080, 1080)])


class TestExportPanelCoordinator(unittest.TestCase):
    def test_on_aspect_ratio_changed_maps_index_and_delegates(self) -> None:
        from fractal_studio.export_panel_coordinator import ExportPanelCoordinator

        class ControllerStub:
            def aspect_mode_from_index(self, index: int) -> str:
                return {0: "square", 1: "portrait", 2: "landscape"}.get(index, "square")

        coordinator = ExportPanelCoordinator(ControllerStub())
        applied: list[tuple[str, bool]] = []

        coordinator.on_aspect_ratio_changed(
            index=2,
            apply_aspect_ratio_mode=lambda mode, update_combo: applied.append((mode, update_combo)),
        )

        self.assertEqual(applied, [("landscape", False)])

    def test_on_export_clicked_uses_combo_index(self) -> None:
        from fractal_studio.export_panel_coordinator import ExportPanelCoordinator

        class ControllerStub:
            def on_export_clicked(self, **kwargs) -> None:
                kwargs["set_custom_size"](640, 480)
                kwargs["export_callback"](640, 480)

        class ComboStub:
            def currentIndex(self) -> int:
                return 1

        coordinator = ExportPanelCoordinator(ControllerStub())
        sizes: list[tuple[int, int]] = []
        exported: list[tuple[int, int]] = []

        coordinator.on_export_clicked(
            export_presets=[("1080 × 1080", 1080, 1080), ("Custom…", 0, 0)],
            export_combo=ComboStub(),
            custom_width_box=None,
            custom_height_box=None,
            set_custom_size=lambda w, h: sizes.append((w, h)),
            export_callback=lambda w, h: exported.append((w, h)),
        )

        self.assertEqual(sizes, [(640, 480)])
        self.assertEqual(exported, [(640, 480)])

    def test_on_export_preset_changed_toggles_custom_visibility(self) -> None:
        from fractal_studio.export_panel_coordinator import ExportPanelCoordinator

        class ControllerStub:
            def should_show_custom_size(self, index: int, presets_count: int) -> bool:
                return index == presets_count - 1

        class SpinStub:
            pass

        coordinator = ExportPanelCoordinator(ControllerStub())
        visibilities: list[bool] = []

        coordinator.on_export_preset_changed(
            index=1,
            export_presets=[("1080 × 1080", 1080, 1080), ("Custom…", 0, 0)],
            custom_width_box=SpinStub(),
            custom_height_box=SpinStub(),
            set_custom_row_visible=visibilities.append,
        )

        self.assertEqual(visibilities, [True])


class TestPaletteWorkflowService(unittest.TestCase):
    def test_save_palette_json_exports_and_reports_status(self) -> None:
        from fractal_studio.palette_service import PaletteWorkflowService

        backend = DummyPaletteBackend()
        service = PaletteWorkflowService()
        messages: list[str] = []
        target = Path(tempfile.mkdtemp(prefix="fs_palette_save_")) / "palette.json"

        result = service.save_palette_json(
            parent=None,
            backend=backend,
            control_points=[(10, 20, 30)],
            palette_size=2048,
            get_save_file_name=lambda *args, **kwargs: (str(target), "PNG"),
            set_status=messages.append,
        )

        self.assertTrue(result)
        self.assertEqual(backend.saved, [(str(target), [(10, 20, 30)], 2048)])
        self.assertEqual(messages[-1], f"Saved palette to {target}")

    def test_load_palette_json_applies_control_points_and_reports_status(self) -> None:
        from fractal_studio.palette_service import PaletteWorkflowService

        backend = DummyPaletteBackend()
        service = PaletteWorkflowService()
        messages: list[str] = []
        control_points: list[tuple[int, int, int]] = []
        target = Path(tempfile.mkdtemp(prefix="fs_palette_load_")) / "palette.json"

        result = service.load_palette_json(
            parent=None,
            backend=backend,
            set_control_points=control_points.extend,
            get_open_file_name=lambda *args, **kwargs: (str(target), "PNG"),
            set_status=messages.append,
        )

        self.assertTrue(result)
        self.assertEqual(backend.loaded_paths, [str(target)])
        self.assertEqual(control_points, [(1, 2, 3), (4, 5, 6)])


class TestPalettePanelCoordinator(unittest.TestCase):
    def test_save_palette_json_returns_false_without_editor(self) -> None:
        from fractal_studio.palette_panel_coordinator import PalettePanelCoordinator

        class WorkflowStub:
            def save_palette_json(self, **kwargs) -> bool:
                raise AssertionError("should not be called")

        coordinator = PalettePanelCoordinator(WorkflowStub())

        result = coordinator.save_palette_json(
            parent=None,
            editor=None,
            backend=object(),
            palette_size=256,
            set_status=lambda _: None,
        )

        self.assertFalse(result)

    def test_load_palette_json_delegates_with_editor(self) -> None:
        from fractal_studio.palette_panel_coordinator import PalettePanelCoordinator

        class EditorStub:
            def set_control_points(self, points) -> None:
                pass

        class WorkflowStub:
            def __init__(self) -> None:
                self.called = False

            def load_palette_json(self, **kwargs) -> bool:
                self.called = True
                return True

        workflow = WorkflowStub()
        coordinator = PalettePanelCoordinator(workflow)

        result = coordinator.load_palette_json(
            parent=None,
            editor=EditorStub(),
            backend=object(),
            set_status=lambda _: None,
        )

        self.assertTrue(result)
        self.assertTrue(workflow.called)

    def test_export_legacy_map_delegates_control_points(self) -> None:
        from fractal_studio.palette_panel_coordinator import PalettePanelCoordinator

        class EditorStub:
            control_points = [(1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12)]

        class WorkflowStub:
            def __init__(self) -> None:
                self.points = None

            def export_legacy_map(self, **kwargs) -> bool:
                self.points = kwargs["control_points"]
                return True

        workflow = WorkflowStub()
        coordinator = PalettePanelCoordinator(workflow)

        result = coordinator.export_legacy_map(
            parent=None,
            editor=EditorStub(),
            backend=object(),
            legacy_palette_size=256,
            set_status=lambda _: None,
        )

        self.assertTrue(result)
        self.assertEqual(workflow.points, EditorStub.control_points)


class TestSidebarWiringCoordinator(unittest.TestCase):
    def test_connect_params_and_viewport_wires_all_expected_signals(self) -> None:
        from fractal_studio.sidebar_wiring_coordinator import SidebarWiringCoordinator

        class SignalStub:
            def __init__(self) -> None:
                self.connected = []

            def connect(self, callback) -> None:
                self.connected.append(callback)

        class ParamsStub:
            def __init__(self) -> None:
                self.formula_changed = SignalStub()
                self.mode_changed = SignalStub()
                self.power_changed = SignalStub()
                self.phoenix_changed = SignalStub()
                self.julia_constant_changed = SignalStub()
                self.max_iterations_changed = SignalStub()
                self.zoom_changed = SignalStub()
                self.coloring_mode_changed = SignalStub()
                self.trap_point_changed = SignalStub()
                self.cycle_toggled = SignalStub()
                self.cycle_speed_changed = SignalStub()

            def set_scale(self, value: float) -> None:
                return None

        class ViewportStub:
            def __init__(self) -> None:
                self.scale_changed = SignalStub()

            def set_formula(self, value: str) -> None:
                return None

            def set_mode(self, value: bool) -> None:
                return None

            def set_power(self, value: int) -> None:
                return None

            def set_phoenix_constant(self, real: float, imag: float) -> None:
                return None

            def set_julia_constant(self, real: float, imag: float) -> None:
                return None

            def set_max_iterations(self, value: int) -> None:
                return None

            def set_scale(self, value: float) -> None:
                return None

            def set_coloring_mode(self, mode: str) -> None:
                return None

            def set_trap_point(self, x: float, y: float) -> None:
                return None

            def set_cycle_active(self, active: bool) -> None:
                return None

            def set_cycle_speed(self, speed: float) -> None:
                return None

        params = ParamsStub()
        viewport = ViewportStub()

        SidebarWiringCoordinator().connect_params_and_viewport(params, viewport)

        self.assertEqual(params.formula_changed.connected, [viewport.set_formula])
        self.assertEqual(params.mode_changed.connected, [viewport.set_mode])
        self.assertEqual(params.power_changed.connected, [viewport.set_power])
        self.assertEqual(params.phoenix_changed.connected, [viewport.set_phoenix_constant])
        self.assertEqual(params.julia_constant_changed.connected, [viewport.set_julia_constant])
        self.assertEqual(params.max_iterations_changed.connected, [viewport.set_max_iterations])
        self.assertEqual(params.zoom_changed.connected, [viewport.set_scale])
        self.assertEqual(viewport.scale_changed.connected, [params.set_scale])
        self.assertEqual(params.coloring_mode_changed.connected, [viewport.set_coloring_mode])
        self.assertEqual(params.trap_point_changed.connected, [viewport.set_trap_point])
        self.assertEqual(params.cycle_toggled.connected, [viewport.set_cycle_active])
        self.assertEqual(params.cycle_speed_changed.connected, [viewport.set_cycle_speed])

    def test_connect_params_and_viewport_ignores_missing_viewport(self) -> None:
        from fractal_studio.sidebar_wiring_coordinator import SidebarWiringCoordinator

        class SignalStub:
            def __init__(self) -> None:
                self.connected = []

            def connect(self, callback) -> None:
                self.connected.append(callback)

        class ParamsStub:
            def __init__(self) -> None:
                self.formula_changed = SignalStub()
                self.mode_changed = SignalStub()
                self.power_changed = SignalStub()
                self.phoenix_changed = SignalStub()
                self.julia_constant_changed = SignalStub()
                self.max_iterations_changed = SignalStub()
                self.zoom_changed = SignalStub()
                self.coloring_mode_changed = SignalStub()
                self.trap_point_changed = SignalStub()
                self.cycle_toggled = SignalStub()
                self.cycle_speed_changed = SignalStub()

        params = ParamsStub()

        SidebarWiringCoordinator().connect_params_and_viewport(params, None)

        self.assertEqual(params.formula_changed.connected, [])
        self.assertEqual(params.cycle_speed_changed.connected, [])

    def test_export_legacy_map_requires_four_control_points(self) -> None:
        from fractal_studio.palette_service import PaletteWorkflowService

        backend = DummyPaletteBackend()
        service = PaletteWorkflowService()
        messages: list[str] = []

        result = service.export_legacy_map(
            parent=None,
            backend=backend,
            control_points=[(1, 2, 3), (4, 5, 6), (7, 8, 9)],
            legacy_palette_size=256,
            get_save_file_name=lambda *args, **kwargs: ("unused", "PNG"),
            set_status=messages.append,
        )

        self.assertFalse(result)
        self.assertEqual(messages[-1], "Add at least four control points before exporting a legacy map.")


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

        self.panel._formula_combo.setCurrentIndex(1)
        self.assertEqual(emitted[-1], "multibrot")
        self.assertTrue(self.panel._power_label.isVisible())
        self.assertTrue(self.panel._power_spin.isVisible())

        self.panel._formula_combo.setCurrentIndex(6)
        self.assertEqual(emitted[-1], "phoenix")
        self.assertTrue(self.panel._phoenix_real_spin.isVisible())

        self.panel._formula_combo.setCurrentIndex(7)
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

        self.panel._mode_combo.setCurrentText("Julia")
        self.panel._coloring_combo.setCurrentIndex(3)
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

    def test_to_state_and_apply_state_round_trip(self) -> None:
        from fractal_studio.state import ParamsState

        state = ParamsState(
            formula="phoenix",
            is_julia=True,
            power=7,
            phoenix_real=0.42,
            phoenix_imag=-0.17,
            julia_real=-0.73,
            julia_imag=0.11,
            max_iterations=640,
            scale=0.025,
            coloring_mode="orbit_trap_point",
            trap_x=0.25,
            trap_y=-0.5,
            cycle_active=True,
            cycle_speed=24.0,
        )
        self.panel.apply_state(state)

        restored = self.panel.to_state()
        self.assertEqual(restored.formula, "phoenix")
        self.assertEqual(restored.power, 7)
        self.assertEqual(restored.coloring_mode, "orbit_trap_point")
        self.assertAlmostEqual(restored.trap_x, 0.25)
        self.assertAlmostEqual(restored.trap_y, -0.5)
        self.assertEqual(restored.max_iterations, 640)
        self.assertTrue(restored.is_julia)


class TestAppearanceSettings(QtWindowTestCase):
    def setUp(self) -> None:
        import fractal_studio.main_window as mwmod

        self._mwmod = mwmod
        self._original_settings_path = mwmod._SETTINGS_PATH
        self._original_favorites_path = mwmod._FAVORITES_PATH
        self._tmpdir = Path(tempfile.mkdtemp(prefix="fs_test_settings_"))
        mwmod._SETTINGS_PATH = self._tmpdir / "settings.json"
        mwmod._FAVORITES_PATH = self._tmpdir / "favorites.json"

    def tearDown(self) -> None:
        self._mwmod._SETTINGS_PATH = self._original_settings_path
        self._mwmod._FAVORITES_PATH = self._original_favorites_path

    def test_appearance_dialog_lists_requested_themes(self) -> None:
        from fractal_studio.main_window import AppearanceSettingsDialog
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QRadioButton

        dialog = AppearanceSettingsDialog("dark")
        preview_requests: list[str] = []
        dialog.theme_preview_requested.connect(preview_requests.append)

        buttons = {button.text().lower(): button for button in dialog.findChildren(QRadioButton)}
        self.assertSetEqual(set(buttons), {"light", "dark", "sepia"})
        self.assertTrue(all(button.isEnabled() for button in buttons.values()))
        self.assertEqual(dialog.selected_theme(), "dark")

        dialog.show()
        QTest.mouseClick(buttons["sepia"], Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(10, 10))
        self.assertEqual(dialog.selected_theme(), "sepia")
        self.assertIn("sepia", preview_requests)

    def test_theme_change_persists_to_settings_file(self) -> None:
        from fractal_studio.persistence import SettingsRepository
        from fractal_studio.state import UiSettings

        SettingsRepository(self._mwmod._SETTINGS_PATH).save(UiSettings(theme="sepia"))

        w = self.make_window()
        self.assertEqual(w._theme_name, "sepia")
        stored = json.loads(self._mwmod._SETTINGS_PATH.read_text())
        self.assertEqual(stored.get("version"), 1)
        self.assertEqual(stored.get("data", {}).get("theme"), "sepia")

    def test_missing_settings_defaults_to_light_theme(self) -> None:
        w = self.make_window()
        self.assertEqual(w._theme_name, "light")

    def test_preview_does_not_persist_settings(self) -> None:
        from fractal_studio.settings_dialog_coordinator import SettingsDialogCoordinator

        class ControllerStub:
            def open_settings_dialog(self, **kwargs) -> None:
                pass

        class SettingsServiceStub:
            def apply_theme_name(self, **kwargs):
                kwargs["apply_theme_to_app"](kwargs["theme_name"])
                return kwargs["theme_name"]

        coordinator = SettingsDialogCoordinator(ControllerStub(), SettingsServiceStub())
        applied: list[str] = []
        persisted: list[str] = []
        refreshed: list[bool] = []

        result = coordinator.apply_theme_name(
            theme_name="dark",
            persist=False,
            current_theme="light",
            apply_theme_to_app=applied.append,
            persist_theme=persisted.append,
            refresh_dynamic_widgets=lambda: refreshed.append(True),
        )

        self.assertEqual(result, "dark")
        self.assertEqual(applied, ["dark"])
        self.assertEqual(persisted, [])
        self.assertEqual(refreshed, [True])

    def test_legacy_settings_file_is_still_supported(self) -> None:
        self._mwmod._SETTINGS_PATH.write_text(json.dumps({"theme": "dark"}))
        w = self.make_window()
        self.assertEqual(w._theme_name, "dark")
        self.assertIn("legacy settings", w.statusBar().currentMessage().lower())

    def test_versioned_settings_file_is_supported(self) -> None:
        self._mwmod._SETTINGS_PATH.write_text(
            json.dumps({"version": 1, "data": {"theme": "sepia"}})
        )
        w = self.make_window()
        self.assertEqual(w._theme_name, "sepia")

    def test_invalid_settings_file_reports_fallback_diagnostic(self) -> None:
        self._mwmod._SETTINGS_PATH.write_text("not json")
        w = self.make_window()
        self.assertIn("ignored invalid settings file", w.statusBar().currentMessage().lower())

    def test_invalid_favorites_file_reports_fallback_diagnostic(self) -> None:
        self._mwmod._FAVORITES_PATH.write_text("not json")
        w = self.make_window()
        self.assertIn("ignored invalid favorites file", w.statusBar().currentMessage().lower())


class TestSettingsWorkflowService(unittest.TestCase):
    def test_backend_state_message_reports_loaded_backend(self) -> None:
        from fractal_studio.settings_service import SettingsWorkflowService

        service = SettingsWorkflowService()

        result = service.backend_state_message(True, True)

        self.assertEqual(result, "Rust extension loaded.")

    def test_startup_message_reports_legacy_settings(self) -> None:
        from fractal_studio.persistence import SettingsLoadResult
        from fractal_studio.settings_service import SettingsWorkflowService
        from fractal_studio.state import UiSettings

        service = SettingsWorkflowService()
        result = service.startup_message(
            SettingsLoadResult(settings=UiSettings(theme="dark"), source="legacy")
        )

        self.assertEqual(result, "Loaded legacy settings file.")

    def test_status_message_reports_legacy_settings_when_backend_missing(self) -> None:
        from fractal_studio.settings_service import SettingsWorkflowService

        service = SettingsWorkflowService()

        result = service.status_message(False, "legacy")

        self.assertEqual(
            result,
            "Fractal Studio ready with scaffold defaults. Loaded legacy settings file.",
        )

    def test_append_diagnostics_joins_non_empty_messages(self) -> None:
        from fractal_studio.settings_service import SettingsWorkflowService

        service = SettingsWorkflowService()

        result = service.append_diagnostics(
            "Fractal Studio ready with Rust backend.",
            ["", "Ignored invalid settings file and loaded defaults.", "  ", "Ignored invalid favorites file and loaded an empty list."],
        )

        self.assertEqual(
            result,
            "Fractal Studio ready with Rust backend. Ignored invalid settings file and loaded defaults. Ignored invalid favorites file and loaded an empty list.",
        )

    def test_startup_status_applies_legacy_message_and_diagnostics(self) -> None:
        from fractal_studio.persistence import SettingsLoadResult
        from fractal_studio.settings_service import SettingsWorkflowService
        from fractal_studio.state import UiSettings

        service = SettingsWorkflowService()

        result = service.startup_status(
            backend_loaded=True,
            load_result=SettingsLoadResult(settings=UiSettings(theme="dark"), source="legacy", diagnostic=""),
            diagnostics=["Ignored invalid favorites file and loaded an empty list."],
        )

        self.assertEqual(
            result,
            "Loaded legacy settings file. Ignored invalid favorites file and loaded an empty list.",
        )

    def test_apply_theme_name_can_preview_without_persisting(self) -> None:
        from fractal_studio.settings_service import SettingsWorkflowService

        service = SettingsWorkflowService()
        events: list[tuple[str, bool]] = []

        service.apply_theme_name(
            theme_name="dark",
            persist=False,
            current_theme="light",
            apply_theme_to_app=lambda theme_name: events.append((theme_name, False)),
            persist_theme=lambda theme_name: events.append((theme_name, True)),
        )

        self.assertEqual(events, [("dark", False)])

    def test_apply_theme_name_persists_when_requested(self) -> None:
        from fractal_studio.settings_service import SettingsWorkflowService

        service = SettingsWorkflowService()
        events: list[tuple[str, bool]] = []

        service.apply_theme_name(
            theme_name="sepia",
            persist=True,
            current_theme="light",
            apply_theme_to_app=lambda theme_name: events.append((theme_name, False)),
            persist_theme=lambda theme_name: events.append((theme_name, True)),
        )

        self.assertEqual(events, [("sepia", False), ("sepia", True)])


class TestWindowStartupCoordinator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def setUp(self) -> None:
        import fractal_studio.main_window as mwmod

        self._mwmod = mwmod
        self._original_settings_path = mwmod._SETTINGS_PATH
        self._tmpdir = Path(tempfile.mkdtemp(prefix="fs_startup_"))
        mwmod._SETTINGS_PATH = self._tmpdir / "settings.json"

    def tearDown(self) -> None:
        self._mwmod._SETTINGS_PATH = self._original_settings_path

    def test_bootstrap_uses_versioned_settings_and_applies_theme(self) -> None:
        from fractal_studio.persistence import SettingsRepository
        from fractal_studio.settings_service import SettingsWorkflowService
        from fractal_studio.startup_coordinator import WindowStartupCoordinator
        from fractal_studio.state import UiSettings

        SettingsRepository(self._mwmod._SETTINGS_PATH).save(UiSettings(theme="sepia"))
        coordinator = WindowStartupCoordinator(
            SettingsRepository(self._mwmod._SETTINGS_PATH),
            SettingsWorkflowService(),
        )

        startup = coordinator.bootstrap(application=_get_app())

        self.assertEqual(startup.theme_name, "sepia")
        self.assertEqual(startup.theme_spec.name, "sepia")
        self.assertEqual(startup.load_result.source, "current")

        message = coordinator.compose_startup_message(
            backend_loaded=True,
            startup_state=startup,
            favorites_diagnostic="",
        )

        self.assertEqual(message, "Fractal Studio ready with Rust backend.")

    def test_bootstrap_reports_legacy_settings_and_diagnostics(self) -> None:
        from fractal_studio.persistence import SettingsRepository
        from fractal_studio.settings_service import SettingsWorkflowService
        from fractal_studio.startup_coordinator import WindowStartupCoordinator

        self._mwmod._SETTINGS_PATH.write_text(json.dumps({"theme": "dark"}))
        coordinator = WindowStartupCoordinator(
            SettingsRepository(self._mwmod._SETTINGS_PATH),
            SettingsWorkflowService(),
        )

        startup = coordinator.bootstrap(
            application=_get_app(),
        )

        self.assertEqual(startup.theme_name, "dark")
        self.assertEqual(startup.theme_spec.name, "dark")
        self.assertEqual(startup.load_result.source, "legacy")

        message = coordinator.compose_startup_message(
            backend_loaded=False,
            startup_state=startup,
            favorites_diagnostic="Ignored invalid favorites file and loaded an empty list.",
        )

        self.assertEqual(
            message,
            "Loaded legacy settings file. Ignored invalid favorites file and loaded an empty list.",
        )


class TestSettingsDialogCoordinator(unittest.TestCase):
    def test_open_settings_dialog_delegates_to_main_window_controller(self) -> None:
        from fractal_studio.settings_dialog_coordinator import SettingsDialogCoordinator

        class ControllerStub:
            def __init__(self) -> None:
                self.called: dict[str, object] | None = None

            def open_settings_dialog(self, **kwargs) -> None:
                self.called = kwargs

        class SettingsServiceStub:
            def apply_theme_name(self, **kwargs):
                return kwargs["theme_name"]

        controller = ControllerStub()
        coordinator = SettingsDialogCoordinator(controller, SettingsServiceStub())
        applied: list[tuple[str, bool]] = []

        coordinator.open_settings_dialog(
            parent=object(),
            current_theme="light",
            dialog_factory=lambda theme, parent: object(),
            apply_theme_name=lambda name, persist: applied.append((name, persist)),
        )

        self.assertIsNotNone(controller.called)
        self.assertEqual(controller.called["current_theme"], "light")

    def test_apply_theme_name_applies_and_refreshes(self) -> None:
        from fractal_studio.settings_dialog_coordinator import SettingsDialogCoordinator

        class ControllerStub:
            def open_settings_dialog(self, **kwargs) -> None:
                pass

        class SettingsServiceStub:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def apply_theme_name(self, **kwargs):
                self.calls.append(kwargs)
                kwargs["apply_theme_to_app"](kwargs["theme_name"])
                kwargs["persist_theme"](kwargs["theme_name"])
                return kwargs["theme_name"]

        service = SettingsServiceStub()
        coordinator = SettingsDialogCoordinator(ControllerStub(), service)
        applied: list[str] = []
        persisted: list[str] = []
        refreshed: list[bool] = []

        result = coordinator.apply_theme_name(
            theme_name="sepia",
            persist=True,
            current_theme="light",
            apply_theme_to_app=applied.append,
            persist_theme=persisted.append,
            refresh_dynamic_widgets=lambda: refreshed.append(True),
        )

        self.assertEqual(result, "sepia")
        self.assertEqual(applied, ["sepia"])
        self.assertEqual(persisted, ["sepia"])
        self.assertEqual(refreshed, [True])


class TestThemeWorkflowCoordinator(unittest.TestCase):
    def test_apply_theme_name_applies_persists_and_returns_updated_spec(self) -> None:
        from fractal_studio.state import UiSettings
        from fractal_studio.theme_workflow_coordinator import ThemeWorkflowCoordinator

        class SettingsDialogStub:
            def apply_theme_name(self, **kwargs):
                if kwargs["theme_name"] != kwargs["current_theme"]:
                    kwargs["apply_theme_to_app"](kwargs["theme_name"])
                if kwargs["persist"]:
                    kwargs["persist_theme"](kwargs["theme_name"])
                kwargs["refresh_dynamic_widgets"]()
                return kwargs["theme_name"]

        class ThemeControllerStub:
            def apply_theme(self, application, theme_name: str):
                return f"spec-{theme_name}"

        class SettingsRepoStub:
            def __init__(self) -> None:
                self.saved: list[UiSettings] = []

            def save(self, settings: UiSettings) -> None:
                self.saved.append(settings)

        refreshed: list[bool] = []
        settings_repo = SettingsRepoStub()
        coordinator = ThemeWorkflowCoordinator(
            SettingsDialogStub(),
            ThemeControllerStub(),
            settings_repo,
        )

        theme_name, theme_spec = coordinator.apply_theme_name(
            theme_name="sepia",
            persist=True,
            current_theme="light",
            current_theme_spec="spec-light",
            application=object(),
            refresh_dynamic_widgets=lambda: refreshed.append(True),
        )

        self.assertEqual(theme_name, "sepia")
        self.assertEqual(theme_spec, "spec-sepia")
        self.assertEqual([setting.theme for setting in settings_repo.saved], ["sepia"])
        self.assertEqual(refreshed, [True])

    def test_apply_theme_name_keeps_current_spec_when_theme_unchanged(self) -> None:
        from fractal_studio.state import UiSettings
        from fractal_studio.theme_workflow_coordinator import ThemeWorkflowCoordinator

        class SettingsDialogStub:
            def apply_theme_name(self, **kwargs):
                if kwargs["theme_name"] != kwargs["current_theme"]:
                    kwargs["apply_theme_to_app"](kwargs["theme_name"])
                if kwargs["persist"]:
                    kwargs["persist_theme"](kwargs["theme_name"])
                kwargs["refresh_dynamic_widgets"]()
                return kwargs["theme_name"]

        class ThemeControllerStub:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def apply_theme(self, application, theme_name: str):
                self.calls.append(theme_name)
                return f"spec-{theme_name}"

        class SettingsRepoStub:
            def __init__(self) -> None:
                self.saved: list[UiSettings] = []

            def save(self, settings: UiSettings) -> None:
                self.saved.append(settings)

        refreshed: list[bool] = []
        theme_controller = ThemeControllerStub()
        settings_repo = SettingsRepoStub()
        coordinator = ThemeWorkflowCoordinator(
            SettingsDialogStub(),
            theme_controller,
            settings_repo,
        )

        theme_name, theme_spec = coordinator.apply_theme_name(
            theme_name="light",
            persist=False,
            current_theme="light",
            current_theme_spec="spec-light",
            application=object(),
            refresh_dynamic_widgets=lambda: refreshed.append(True),
        )

        self.assertEqual(theme_name, "light")
        self.assertEqual(theme_spec, "spec-light")
        self.assertEqual(theme_controller.calls, [])
        self.assertEqual(settings_repo.saved, [])
        self.assertEqual(refreshed, [True])


class TestPalettePreviewCoordinator(unittest.TestCase):
    def test_update_control_summary_sets_expected_text(self) -> None:
        from fractal_studio.palette_preview_coordinator import PalettePreviewCoordinator

        class FavoritesControllerStub:
            def update_palette_previews(self, **kwargs) -> None:
                pass

        class LabelStub:
            def __init__(self) -> None:
                self.text = ""

            def setText(self, text: str) -> None:
                self.text = text

        coordinator = PalettePreviewCoordinator(FavoritesControllerStub())
        label = LabelStub()

        coordinator.update_control_summary(label, [(1, 2, 3), (4, 5, 6)])

        self.assertEqual(label.text, "2 control points")

    def test_update_palette_previews_delegates_to_favorites_controller(self) -> None:
        from fractal_studio.palette_preview_coordinator import PalettePreviewCoordinator

        class FavoritesControllerStub:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def update_palette_previews(self, **kwargs) -> None:
                self.calls.append(kwargs)

        controller = FavoritesControllerStub()
        coordinator = PalettePreviewCoordinator(controller)
        marker = object()

        coordinator.update_palette_previews(
            palette=[(1, 2, 3)],
            editor=marker,
            backend=marker,
            legacy_palette_size=256,
            preview_palette=marker,
            preview_legacy=marker,
            palette_summary=marker,
        )

        self.assertEqual(len(controller.calls), 1)
        self.assertEqual(controller.calls[0]["palette"], [(1, 2, 3)])
        self.assertEqual(controller.calls[0]["legacy_palette_size"], 256)


class TestThumbnailHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

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


class TestThemeController(unittest.TestCase):
    def test_refresh_dynamic_widgets_repolishes_hover_panel_and_rows(self) -> None:
        from fractal_studio.theme_controller import ThemeController

        class FakeStyle:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def unpolish(self, widget) -> None:
                self.calls.append("unpolish")

            def polish(self, widget) -> None:
                self.calls.append("polish")

        class FakeHoverPanel:
            def __init__(self) -> None:
                self._style = FakeStyle()

            def style(self):
                return self._style

        class FakeRow:
            def __init__(self) -> None:
                self.applied = 0

            def _apply_visual_state(self) -> None:
                self.applied += 1

        controller = ThemeController()
        hover_panel = FakeHoverPanel()
        rows = [FakeRow(), FakeRow()]

        controller.refresh_dynamic_widgets(hover_panel, rows)

        self.assertEqual(hover_panel.style().calls, ["unpolish", "polish"])
        self.assertEqual(rows[0].applied, 1)
        self.assertEqual(rows[1].applied, 1)

    def test_build_stylesheet_keeps_expected_sections(self) -> None:
        from fractal_studio.theme import build_stylesheet, get_theme

        stylesheet = build_stylesheet(get_theme("light"))

        self.assertIn("QMainWindow, QDialog", stylesheet)
        self.assertIn("QLabel#hoverPanel", stylesheet)
        self.assertIn("QDialog#settingsDialog", stylesheet)


class TestFavoriteHoverPresenter(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def _favorite(self, **overrides):
        favorite = {
            "name": "Sample",
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
        favorite.update(overrides)
        return favorite

    def test_build_stats_html_contains_core_values(self) -> None:
        from fractal_studio.favorite_hover_presenter import FavoriteHoverPresenter
        from PySide6.QtWidgets import QWidget

        presenter = FavoriteHoverPresenter()
        row = QWidget()

        html = presenter.build_stats_html(row, self._favorite())

        self.assertIn("Mandelbrot", html)
        self.assertIn("-0.750000", html)
        self.assertIn("Iterations", html)

    def test_hide_hides_hover_panel(self) -> None:
        from fractal_studio.favorite_hover_presenter import FavoriteHoverPresenter
        from PySide6.QtWidgets import QLabel

        presenter = FavoriteHoverPresenter()
        panel = QLabel("hover")
        panel.show()

        presenter.hide(panel)

        self.assertFalse(panel.isVisible())


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

    def _face_rect(self, editor, face: int) -> tuple[float, float, float, float]:
        margin = 12.0
        size = min((editor.width() - margin * 2) / 3.0, (editor.height() - margin * 2) / 3.0)
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
        self.assertTrue(any(status.startswith("Dragging control point 0 on face 2") for status in statuses))

    def test_mouse_press_adds_point_and_hover_status(self) -> None:
        editor = self._make_editor()
        statuses: list[str] = []
        editor.status_changed.connect(statuses.append)
        pos = self._face_center_point(editor, 2)
        self._click(editor, pos)
        self.assertEqual(len(editor.control_points), 1)
        self.assertTrue(any(status.startswith("Added control point 0 on face 2") for status in statuses))

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

    def test_viewport_apply_state_and_to_state(self) -> None:
        from fractal_studio.backend import load_backend
        from fractal_studio.state import ViewportState
        from fractal_studio.viewport import FractalViewportWidget

        viewport = FractalViewportWidget(load_backend())
        state = ViewportState(
            formula="multibrot",
            center_x=-0.123,
            center_y=0.456,
            scale=0.0025,
            max_iterations=700,
            is_julia=True,
            julia_real=-0.81,
            julia_imag=0.156,
            power=5,
            phoenix_real=0.4,
            phoenix_imag=-0.2,
            coloring_mode="orbit_trap_cross",
            trap_x=0.1,
            trap_y=-0.1,
            palette_offset=0.25,
        )

        viewport.apply_state(state, rerender=False)
        restored = viewport.to_state()

        self.assertEqual(restored.formula, "multibrot")
        self.assertAlmostEqual(restored.center_x, -0.123)
        self.assertAlmostEqual(restored.center_y, 0.456)
        self.assertAlmostEqual(restored.scale, 0.0025)
        self.assertEqual(restored.max_iterations, 700)
        self.assertEqual(restored.power, 5)
        self.assertEqual(restored.coloring_mode, "orbit_trap_cross")


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
        row, hover_panel, _, _ = self._make_row()
        self._enter_row(row)
        self.assertIn("Mandelbrot", hover_panel.text())
        self.assertIn("-0.750000", hover_panel.text())

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
                hover_panel = QLabel()
                row = FavoriteThumbnailRow(pixmap, fav, hover_panel, lambda _: None)
                self._enter_row(row)
                self.assertIn(expected, hover_panel.text())


class TestFavoriteRowStylePresenter(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def test_apply_visual_state_selected(self) -> None:
        from fractal_studio.favorite_row_style_presenter import FavoriteRowStylePresenter
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
        from fractal_studio.favorite_row_style_presenter import FavoriteRowStylePresenter
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
        from fractal_studio.favorite_row_style_presenter import FavoriteRowStylePresenter
        from PySide6.QtWidgets import QLabel, QWidget

        presenter = FavoriteRowStylePresenter()
        row = QWidget()
        thumb = QLabel()
        name = QLabel()

        presenter.apply_visual_state(row, thumb, name, selected=False, hovered=False)

        self.assertIn("transparent", row.styleSheet())
        self.assertIn("transparent", thumb.styleSheet())
        self.assertEqual(name.styleSheet(), "")


class TestFavoritePersistence(QtWindowTestCase):
    def _activate_row(self, window, index: int = -1) -> None:
        from fractal_studio.main_window import FavoriteThumbnailRow
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        rows = window.findChildren(FavoriteThumbnailRow)
        self.assertGreater(len(rows), 0)
        row = rows[index]
        row.show()
        QTest.mouseDClick(row, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(10, 10))

    def _save_favorite_via_ui(self, window) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QPushButton

        save_buttons = [button for button in window.findChildren(QPushButton) if button.text() == "Save"]
        self.assertEqual(len(save_buttons), 1)
        QTest.mouseClick(save_buttons[0], Qt.MouseButton.LeftButton)

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
        self._save_favorite_via_ui(w)
        w.editor.set_control_points(replacement_points)

        self._activate_row(w)

        self.assertEqual(w.editor.control_points, initial_points)

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
        from fractal_studio.main_window import FavoriteThumbnailRow

        self._save_favorite_via_ui(w)
        self.assertEqual(len(w.findChildren(FavoriteThumbnailRow)), 1)

        self._activate_row(w, 0)
        original_center_x = w.viewport.to_state().center_x
        current_state = w.viewport.to_state()
        w.viewport.apply_state(replace(current_state, center_x=current_state.center_x + 0.5))
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

        original_points = [(20, 30, 40), (60, 80, 100), (120, 140, 160), (200, 220, 240)]
        different_points = [(5, 10, 15), (25, 35, 45), (85, 95, 105), (145, 155, 165)]

        w.editor.set_control_points(original_points)
        expected_palette = w.viewport.palette()
        self._save_favorite_via_ui(w)

        w.editor.set_control_points(different_points)
        self.assertNotEqual(w.viewport.palette(), expected_palette)

        self._activate_row(w)

        self.assertEqual(w.viewport.palette(), expected_palette)

    def test_load_favorites_from_disk_returns_empty_for_missing_or_corrupt_file(self) -> None:
        from fractal_studio.persistence import FavoritesRepository

        repo = FavoritesRepository(self._mwmod._FAVORITES_PATH)

        self.assertEqual(repo.load(), [])
        self.assertEqual(repo.last_load_diagnostic, "")
        self._mwmod._FAVORITES_PATH.write_text("not json")
        self.assertEqual(repo.load(), [])
        self.assertIn("ignored invalid favorites file", repo.last_load_diagnostic.lower())

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

    def test_load_favorites_supports_versioned_format_with_empty_favorites(self) -> None:
        from fractal_studio.persistence import FavoritesRepository

        self._mwmod._FAVORITES_PATH.write_text(
            json.dumps({"version": 1, "favorites": []})
        )

        loaded = FavoritesRepository(self._mwmod._FAVORITES_PATH).load()
        self.assertEqual(len(loaded), 0)


class TestFavoritesController(unittest.TestCase):
    def test_persist_favorites_filters_invalid_entries(self) -> None:
        from fractal_studio.favorites_controller import FavoritesController

        captured: list[list[object]] = []
        controller = FavoritesController()

        controller.persist_favorites(
            favorites=[{"id": "1"}, "skip-me", {"id": "2"}],
            save_to_repo=lambda snapshots: captured.append(snapshots),
        )

        self.assertEqual(len(captured), 1)
        self.assertEqual([snapshot.to_dict()["id"] for snapshot in captured[0]], ["1", "2"])

    def test_load_favorites_converts_snapshots_to_dicts(self) -> None:
        from fractal_studio.favorites_controller import FavoritesController
        from fractal_studio.state import FavoriteSnapshot, ViewportState

        controller = FavoritesController()
        snapshot = FavoriteSnapshot(
            favorite_id="fav-1",
            saved_at="2026-05-25T12:34:56",
            aspect_ratio_mode="square",
            name="Favorite",
            viewport=ViewportState(
                formula="Mandelbrot",
                center_x=-0.75,
                center_y=0.1,
                scale=0.003,
                max_iterations=256,
                is_julia=False,
                julia_real=0.0,
                julia_imag=0.0,
                power=2,
                phoenix_real=0.0,
                phoenix_imag=0.0,
                coloring_mode="smooth",
                trap_x=0.0,
                trap_y=0.0,
                palette_offset=0.0,
            ),
            control_points=[(1, 2, 3)],
            palette=[(4, 5, 6)],
            thumbnail="thumb",
        )

        loaded = controller.load_favorites(lambda: [snapshot])

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["id"], "fav-1")
        self.assertEqual(loaded[0]["name"], "Favorite")
    def test_build_favorite_name_adds_suffix_when_base_exists(self) -> None:
        from fractal_studio.backend import default_profile
        from fractal_studio.favorites_controller import FavoritesController
        from fractal_studio.state import ViewportState

        controller = FavoritesController()
        state = ViewportState(
            formula="Mandelbrot",
            center_x=-0.75,
            center_y=0.1,
            scale=0.003,
            max_iterations=256,
            is_julia=False,
            julia_real=0.0,
            julia_imag=0.0,
            power=2,
            phoenix_real=0.0,
            phoenix_imag=0.0,
            coloring_mode=default_profile().coloring_model,
            trap_x=0.0,
            trap_y=0.0,
            palette_offset=0.0,
        )

        def fixed_now() -> object:
            import datetime

            return datetime.datetime(2026, 5, 25, 12, 34, 56)

        base_name = "Mandelbrot (-0.750, 0.100) 2026-05-25 12:34:56"
        result = controller.build_favorite_name(state, {base_name, f"{base_name} (2)"}, fixed_now)

        self.assertEqual(result, f"{base_name} (3)")

    def test_build_favorite_name_uses_base_when_available(self) -> None:
        from fractal_studio.backend import default_profile
        from fractal_studio.favorites_controller import FavoritesController
        from fractal_studio.state import ViewportState

        controller = FavoritesController()
        state = ViewportState(
            formula="Mandelbrot",
            center_x=-0.75,
            center_y=0.1,
            scale=0.003,
            max_iterations=256,
            is_julia=False,
            julia_real=0.0,
            julia_imag=0.0,
            power=2,
            phoenix_real=0.0,
            phoenix_imag=0.0,
            coloring_mode=default_profile().coloring_model,
            trap_x=0.0,
            trap_y=0.0,
            palette_offset=0.0,
        )

        def fixed_now() -> object:
            import datetime

            return datetime.datetime(2026, 5, 25, 12, 34, 56)

        result = controller.build_favorite_name(state, set(), fixed_now)

        self.assertEqual(result, "Mandelbrot (-0.750, 0.100) 2026-05-25 12:34:56")

    def test_save_favorite_orchestrates_callbacks(self) -> None:
        from fractal_studio.backend import default_profile
        from fractal_studio.favorites_controller import FavoritesController
        from fractal_studio.state import ViewportState

        class ViewportStub:
            def __init__(self) -> None:
                self._palette = [(9, 8, 7)]

            def to_state(self) -> ViewportState:
                return ViewportState(
                    formula="Mandelbrot",
                    center_x=-0.75,
                    center_y=0.1,
                    scale=0.003,
                    max_iterations=256,
                    is_julia=False,
                    julia_real=0.0,
                    julia_imag=0.0,
                    power=2,
                    phoenix_real=0.0,
                    phoenix_imag=0.0,
                    coloring_mode=default_profile().coloring_model,
                    trap_x=0.0,
                    trap_y=0.0,
                    palette_offset=0.0,
                )

            def palette(self) -> list[tuple[int, int, int]]:
                return list(self._palette)

        controller = FavoritesController()
        viewport = ViewportStub()
        calls: list[object] = []

        snapshot = controller.save_favorite(
            viewport=viewport,
            editor=None,
            aspect_ratio_mode="square",
            favorites=[],
            build_name=lambda state: f"{state.formula} saved",
            capture_thumbnail=lambda: "thumb",
            add_favorite=lambda fav: calls.append(("favorite", fav["name"])),
            add_row=lambda fav: calls.append(("row", fav["thumbnail"])),
            persist=lambda: calls.append("persist"),
            show_status=lambda text: calls.append(("status", text)),
        )

        self.assertEqual(snapshot.name, "Mandelbrot saved")
        self.assertEqual(calls[0], ("favorite", "Mandelbrot saved"))
        self.assertEqual(calls[1], ("row", "thumb"))
        self.assertEqual(calls[2], "persist")
        self.assertEqual(calls[3], ("status", "Saved favorite: Mandelbrot saved"))

    def test_load_favorite_row_orchestrates_restore_and_selection(self) -> None:
        from fractal_studio.backend import default_profile
        from fractal_studio.favorites_controller import FavoritesController
        from fractal_studio.state import FavoriteSnapshot, ViewportState

        class ViewportStub:
            def __init__(self) -> None:
                self.applied: list[tuple[bool, str]] = []
                self.palette: list[tuple[int, int, int]] = []

            def apply_state(self, state, rerender: bool = True) -> None:
                self.applied.append((rerender, state.formula))

            def set_cycle_active(self, active: bool) -> None:
                self.applied.append((active, "cycle"))

            def set_palette(self, palette) -> None:
                self.palette = list(palette)

        class ParamsStub:
            def __init__(self) -> None:
                self.applied = []

            def apply_state(self, state) -> None:
                self.applied.append(state.formula)

        class EditorStub:
            def __init__(self) -> None:
                self.points = []

            def set_control_points(self, points) -> None:
                self.points = list(points)

        class PreviewStub:
            def __init__(self) -> None:
                self.palette = []

            def set_palette(self, palette) -> None:
                self.palette = list(palette)

        controller = FavoritesController()
        viewport = ViewportStub()
        params_panel = ParamsStub()
        editor = EditorStub()
        preview_palette = PreviewStub()
        state = ViewportState(
            formula="Mandelbrot",
            center_x=-0.75,
            center_y=0.1,
            scale=0.003,
            max_iterations=256,
            is_julia=False,
            julia_real=0.0,
            julia_imag=0.0,
            power=2,
            phoenix_real=0.0,
            phoenix_imag=0.0,
            coloring_mode=default_profile().coloring_model,
            trap_x=0.0,
            trap_y=0.0,
            palette_offset=0.0,
        )
        snapshot = FavoriteSnapshot(
            favorite_id="1",
            saved_at="now",
            aspect_ratio_mode="portrait",
            name="Saved Favorite",
            viewport=state,
            control_points=[(1, 2, 3)],
            palette=[(9, 8, 7)],
            thumbnail="thumb",
        )
        favorites = [snapshot.to_dict()]
        rows = [object()]
        selected: list[object] = []
        messages: list[str] = []
        aspect_modes: list[str] = []

        controller.load_favorite_row(
            row=rows[0],
            favorites=favorites,
            rows=rows,
            viewport=viewport,
            params_panel=params_panel,
            editor=editor,
            preview_palette=preview_palette,
            apply_aspect_ratio_mode=aspect_modes.append,
            select_row=selected.append,
            show_status=messages.append,
        )

        self.assertEqual(aspect_modes, ["portrait"])
        self.assertEqual(selected, [rows[0]])
        self.assertEqual(messages, ["Restored: Saved Favorite"])
        self.assertEqual(editor.points, [(1, 2, 3)])
        self.assertEqual(preview_palette.palette, [(9, 8, 7)])

    def test_update_palette_previews_sets_summary_and_preview_palettes(self) -> None:
        from fractal_studio.backend import default_profile
        from fractal_studio.favorites_controller import FavoritesController

        class EditorStub:
            def __init__(self) -> None:
                self.control_points = [(10, 20, 30), (40, 50, 60), (70, 80, 90), (100, 110, 120)]

        class PaletteStub:
            def __init__(self) -> None:
                self.palette = []

            def set_palette(self, palette) -> None:
                self.palette = list(palette)

        class LabelStub:
            def __init__(self) -> None:
                self.text = ""

            def setText(self, text: str) -> None:
                self.text = text

        class BackendStub:
            available = True

            def generate_palette(self, control_points, palette_size):
                return list(control_points[:palette_size])

        controller = FavoritesController()
        palette_preview = PaletteStub()
        legacy_preview = PaletteStub()
        summary = LabelStub()
        editor = EditorStub()
        backend = BackendStub()

        controller.update_palette_previews(
            palette=[(1, 2, 3), (4, 5, 6)],
            editor=editor,
            backend=backend,
            legacy_palette_size=default_profile().legacy_palette_size,
            preview_palette=palette_preview,
            preview_legacy=legacy_preview,
            palette_summary=summary,
        )

        self.assertEqual(palette_preview.palette, [(1, 2, 3), (4, 5, 6)])
        self.assertEqual(legacy_preview.palette, editor.control_points)
        self.assertIn("Generated 2 internal colors", summary.text)


class TestFavoritesPanelCoordinator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def test_build_row_uses_placeholder_for_invalid_thumbnail(self) -> None:
        from fractal_studio.favorites_panel_coordinator import FavoritesPanelCoordinator
        from PySide6.QtGui import QColor, QPixmap
        from PySide6.QtWidgets import QLabel

        coordinator = FavoritesPanelCoordinator(hover_presenter=object())
        hover_panel = QLabel()
        captured: dict[str, object] = {}

        def row_factory(*args, **kwargs):
            captured["pixmap"] = args[0]
            captured["hover_presenter"] = kwargs.get("hover_presenter")
            return object()

        def placeholder() -> QPixmap:
            pixmap = QPixmap(8, 8)
            pixmap.fill(QColor("#ff0000"))
            return pixmap

        row = coordinator.build_row(
            favorite={"name": "sample", "thumbnail": "broken"},
            hover_panel=hover_panel,
            on_select=lambda _: None,
            on_activate=lambda _: None,
            row_factory=row_factory,
            decode_thumbnail=lambda _: QPixmap(),
            placeholder_pixmap=placeholder,
        )

        self.assertIsNotNone(row)
        self.assertFalse(captured["pixmap"].isNull())

    def test_select_row_deselects_previous(self) -> None:
        from fractal_studio.favorites_panel_coordinator import FavoritesPanelCoordinator

        class Row:
            def __init__(self) -> None:
                self.calls: list[bool] = []

            def set_selected(self, selected: bool) -> None:
                self.calls.append(selected)

        coordinator = FavoritesPanelCoordinator(hover_presenter=object())
        old_row = Row()
        new_row = Row()

        selected = coordinator.select_row(old_row, new_row)

        self.assertIs(selected, new_row)
        self.assertEqual(old_row.calls, [False])
        self.assertEqual(new_row.calls, [True])

    def test_delete_selected_removes_row_and_favorite(self) -> None:
        from fractal_studio.favorites_panel_coordinator import FavoritesPanelCoordinator

        class Row:
            def __init__(self, name: str) -> None:
                self.name = name
                self.deleted = False

            def set_selected(self, selected: bool) -> None:
                pass

            def deleteLater(self) -> None:
                self.deleted = True

        class Layout:
            def __init__(self) -> None:
                self.removed: list[Row] = []

            def removeWidget(self, row: Row) -> None:
                self.removed.append(row)

        coordinator = FavoritesPanelCoordinator(hover_presenter=object())
        row_a = Row("a")
        row_b = Row("b")
        rows = [row_a, row_b]
        favorites = [{"id": "a"}, {"id": "b"}]
        layout = Layout()

        selected = coordinator.delete_selected(
            selected_row=row_b,
            rows=rows,
            favorites=favorites,
            scroll_layout=layout,
        )

        self.assertIsNone(selected)
        self.assertEqual(rows, [row_a])
        self.assertEqual(favorites, [{"id": "a"}])
        self.assertEqual(layout.removed, [row_b])
        self.assertTrue(row_b.deleted)

    def test_build_row_with_callbacks_invokes_owner_handlers(self) -> None:
        from fractal_studio.favorites_panel_coordinator import FavoritesPanelCoordinator
        from PySide6.QtGui import QColor, QPixmap
        from PySide6.QtWidgets import QLabel

        coordinator = FavoritesPanelCoordinator(hover_presenter=object())
        hover_panel = QLabel()
        captured: dict[str, object] = {}

        class Owner:
            def __init__(self) -> None:
                self.selected: list[object] = []
                self.activated: list[object] = []

            def on_selected(self, row: object) -> None:
                self.selected.append(row)

            def on_activated(self, row: object) -> None:
                self.activated.append(row)

        owner = Owner()

        def row_factory(*args, **kwargs):
            captured["on_select"] = args[3]
            captured["on_activate"] = args[4]
            return object()

        def placeholder() -> QPixmap:
            pixmap = QPixmap(8, 8)
            pixmap.fill(QColor("#00ff00"))
            return pixmap

        row = coordinator.build_row_with_callbacks(
            favorite={"name": "sample", "thumbnail": "broken"},
            owner=owner,
            hover_panel=hover_panel,
            on_select_row=lambda current_owner, current_row: current_owner.on_selected(current_row),
            on_activate_row=lambda current_owner, current_row: current_owner.on_activated(current_row),
            row_factory=row_factory,
            decode_thumbnail=lambda _: QPixmap(),
            placeholder_pixmap=placeholder,
        )

        captured["on_select"](row)
        captured["on_activate"](row)

        self.assertEqual(owner.selected, [row])
        self.assertEqual(owner.activated, [row])

    def test_build_row_with_callbacks_noops_after_owner_collected(self) -> None:
        from fractal_studio.favorites_panel_coordinator import FavoritesPanelCoordinator
        from PySide6.QtGui import QColor, QPixmap
        from PySide6.QtWidgets import QLabel

        coordinator = FavoritesPanelCoordinator(hover_presenter=object())
        hover_panel = QLabel()
        captured: dict[str, object] = {}
        calls: list[str] = []

        class Owner:
            pass

        owner = Owner()

        def row_factory(*args, **kwargs):
            captured["on_select"] = args[3]
            captured["on_activate"] = args[4]
            return object()

        def placeholder() -> QPixmap:
            pixmap = QPixmap(8, 8)
            pixmap.fill(QColor("#0000ff"))
            return pixmap

        coordinator.build_row_with_callbacks(
            favorite={"name": "sample", "thumbnail": "broken"},
            owner=owner,
            hover_panel=hover_panel,
            on_select_row=lambda current_owner, current_row: calls.append("select"),
            on_activate_row=lambda current_owner, current_row: calls.append("activate"),
            row_factory=row_factory,
            decode_thumbnail=lambda _: QPixmap(),
            placeholder_pixmap=placeholder,
        )

        del owner
        gc.collect()
        captured["on_select"](object())
        captured["on_activate"](object())

        self.assertEqual(calls, [])


class TestFavoritesWorkflowCoordinator(unittest.TestCase):
    def test_save_favorite_returns_early_without_viewport(self) -> None:
        from fractal_studio.favorites_workflow_coordinator import FavoritesWorkflowCoordinator

        class ControllerStub:
            def __init__(self) -> None:
                self.called = False

            def save_favorite(self, **kwargs):
                self.called = True

            def build_favorite_name(self, state, existing_names, now):
                return "unused"

        class PanelStub:
            def delete_selected(self, **kwargs):
                return kwargs["selected_row"]

        controller = ControllerStub()
        coordinator = FavoritesWorkflowCoordinator(controller, PanelStub())

        coordinator.save_favorite(
            viewport=None,
            editor=None,
            aspect_ratio_mode="square",
            favorites=[],
            build_name=lambda state: "name",
            capture_thumbnail=lambda: "thumb",
            add_favorite=lambda fav: None,
            add_row=lambda fav: None,
            persist_favorites=lambda: None,
            show_status=lambda msg: None,
        )

        self.assertFalse(controller.called)

    def test_load_selected_favorite_calls_load_row_only_when_ready(self) -> None:
        from fractal_studio.favorites_workflow_coordinator import FavoritesWorkflowCoordinator

        class ControllerStub:
            def save_favorite(self, **kwargs):
                return None

            def build_favorite_name(self, state, existing_names, now):
                return "unused"

        class PanelStub:
            def delete_selected(self, **kwargs):
                return kwargs["selected_row"]

        coordinator = FavoritesWorkflowCoordinator(ControllerStub(), PanelStub())
        calls: list[object] = []

        coordinator.load_selected_favorite(
            viewport=object(),
            params_panel=object(),
            selected_row="row-1",
            load_row=calls.append,
        )
        coordinator.load_selected_favorite(
            viewport=None,
            params_panel=object(),
            selected_row="row-2",
            load_row=calls.append,
        )
        coordinator.load_selected_favorite(
            viewport=object(),
            params_panel=None,
            selected_row="row-3",
            load_row=calls.append,
        )
        coordinator.load_selected_favorite(
            viewport=object(),
            params_panel=object(),
            selected_row=None,
            load_row=calls.append,
        )

        self.assertEqual(calls, ["row-1"])

    def test_delete_selected_favorite_persists_when_selection_cleared(self) -> None:
        from fractal_studio.favorites_workflow_coordinator import FavoritesWorkflowCoordinator

        class ControllerStub:
            def save_favorite(self, **kwargs):
                return None

            def build_favorite_name(self, state, existing_names, now):
                return "unused"

        class PanelStub:
            def delete_selected(self, **kwargs):
                return None

        coordinator = FavoritesWorkflowCoordinator(ControllerStub(), PanelStub())
        persisted: list[str] = []

        selected = coordinator.delete_selected_favorite(
            selected_row=object(),
            rows=[object()],
            favorites=[{"id": "a"}],
            scroll_layout=object(),
            persist_favorites=lambda: persisted.append("saved"),
        )

        self.assertIsNone(selected)
        self.assertEqual(persisted, ["saved"])

    def test_build_favorite_name_delegates_with_existing_names(self) -> None:
        from fractal_studio.favorites_workflow_coordinator import FavoritesWorkflowCoordinator
        from fractal_studio.state import ViewportState

        class ControllerStub:
            def __init__(self) -> None:
                self.existing_names: set[str] | None = None

            def save_favorite(self, **kwargs):
                return None

            def build_favorite_name(self, state, existing_names, now):
                self.existing_names = existing_names
                return "resolved-name"

        class PanelStub:
            def delete_selected(self, **kwargs):
                return kwargs["selected_row"]

        controller = ControllerStub()
        coordinator = FavoritesWorkflowCoordinator(controller, PanelStub())
        state = ViewportState(
            formula="Mandelbrot",
            center_x=-0.75,
            center_y=0.1,
            scale=0.003,
            max_iterations=256,
            is_julia=False,
            julia_real=0.0,
            julia_imag=0.0,
            power=2,
            phoenix_real=0.0,
            phoenix_imag=0.0,
            coloring_mode="smooth",
            trap_x=0.0,
            trap_y=0.0,
            palette_offset=0.0,
        )

        name = coordinator.build_favorite_name(
            state=state,
            favorites=[{"name": "A"}, {"name": "B"}, {}],
            now=lambda: None,
        )

        self.assertEqual(name, "resolved-name")
        self.assertEqual(controller.existing_names, {"A", "B", ""})


if __name__ == "__main__":
    unittest.main()
