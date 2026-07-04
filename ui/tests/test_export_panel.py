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
class TestCustomResolutionDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_app()

    def test_default_values(self) -> None:
        from fractal_studio.ui.dialogs.custom_resolution_dialog import (
            CustomResolutionDialog,
        )

        dlg = CustomResolutionDialog(1920, 1080)
        self.assertEqual(dlg.values(), (1920, 1080))

    def test_custom_values(self) -> None:
        from fractal_studio.ui.dialogs.custom_resolution_dialog import (
            CustomResolutionDialog,
        )

        dlg = CustomResolutionDialog(3840, 2160)
        self.assertEqual(dlg.values(), (3840, 2160))

    def test_spinbox_range(self) -> None:
        from fractal_studio.ui.dialogs.custom_resolution_dialog import (
            CustomResolutionDialog,
        )

        dlg = CustomResolutionDialog(1920, 1080)
        dlg._width_box.setValue(0)
        dlg._height_box.setValue(-1)
        self.assertEqual(dlg.values(), (64, 64))

        dlg._width_box.setValue(99999)
        dlg._height_box.setValue(99999)
        self.assertEqual(dlg.values(), (16384, 16384))


@pytest.mark.integration
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
        from fractal_studio.application.controllers.export_controller import (
            ExportController,
        )

        controller = ExportController(export_service=object())
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

    def test_main_window_sections_state_hides_export_aliases(self) -> None:
        w = self.make_window()

        self.assertIsNotNone(self._find_export_combo(w))
        with self.assertRaises(AttributeError):
            _ = w._sections_state.export_combo


@pytest.mark.integration
class TestExportPanelCoordinator(unittest.TestCase):
    def test_on_aspect_ratio_changed_maps_index_and_delegates(self) -> None:
        from fractal_studio.application.coordinators.export_panel_coordinator import (
            ExportPanelCoordinator,
        )

        class ControllerStub:
            def aspect_mode_from_index(self, index: int) -> str:
                return {0: "square", 1: "portrait", 2: "landscape"}.get(index, "square")

        coordinator = ExportPanelCoordinator(ControllerStub())
        applied: list[tuple[str, bool]] = []

        coordinator.on_aspect_ratio_changed(
            index=2,
            apply_aspect_ratio_mode=lambda mode, update_combo: applied.append(
                (mode, update_combo)
            ),
        )

        self.assertEqual(applied, [("landscape", False)])

    def test_on_export_clicked_uses_combo_index(self) -> None:
        from fractal_studio.application.coordinators.export_panel_coordinator import (
            ExportPanelCoordinator,
        )

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
        from fractal_studio.application.coordinators.export_panel_coordinator import (
            ExportPanelCoordinator,
        )

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


