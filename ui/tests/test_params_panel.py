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
class TestSidebarWiringCoordinator(unittest.TestCase):
    def test_connect_params_and_viewport_wires_all_expected_signals(self) -> None:
        from fractal_studio.application.coordinators.sidebar_wiring_coordinator import (
            SidebarWiringCoordinator,
        )

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
        self.assertEqual(
            params.phoenix_changed.connected, [viewport.set_phoenix_constant]
        )
        self.assertEqual(
            params.julia_constant_changed.connected, [viewport.set_julia_constant]
        )
        self.assertEqual(
            params.max_iterations_changed.connected, [viewport.set_max_iterations]
        )
        self.assertEqual(params.zoom_changed.connected, [viewport.set_scale])
        self.assertEqual(viewport.scale_changed.connected, [params.set_scale])
        self.assertEqual(
            params.coloring_mode_changed.connected, [viewport.set_coloring_mode]
        )
        self.assertEqual(params.trap_point_changed.connected, [viewport.set_trap_point])
        self.assertEqual(params.cycle_toggled.connected, [viewport.set_cycle_active])
        self.assertEqual(
            params.cycle_speed_changed.connected, [viewport.set_cycle_speed]
        )

    def test_connect_params_and_viewport_ignores_missing_viewport(self) -> None:
        from fractal_studio.application.coordinators.sidebar_wiring_coordinator import (
            SidebarWiringCoordinator,
        )

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
        from fractal_studio.services.palette_service import PaletteWorkflowService

        backend = DummyPaletteBackend()
        service = PaletteWorkflowService()
        messages: list[str] = []

        result = service.export_legacy_map(
            path=None,
            backend=backend,
            control_points=[(1, 2, 3), (4, 5, 6), (7, 8, 9)],
            legacy_palette_size=256,
            set_status=messages.append,
        )

        self.assertFalse(result)
        self.assertEqual(
            messages[-1],
            "Add at least four control points before exporting a legacy map.",
        )


@pytest.mark.integration
class TestParamsPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_app()

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
        from fractal_studio.state import PhoenixParams, ParamsState

        state = ParamsState(
            formula="phoenix",
            is_julia=True,
            power=7,
            formula_params=PhoenixParams(real=0.42, imag=-0.17),
            max_iterations=640,
            scale=0.025,
            coloring_mode="orbit_trap_point",
            cycle_active=True,
            cycle_speed=24.0,
        )
        self.panel.apply_state(state)

        restored = self.panel.to_state()
        self.assertEqual(restored.formula, "phoenix")
        self.assertEqual(restored.power, 7)
        self.assertEqual(restored.coloring_mode, "orbit_trap_point")
        self.assertAlmostEqual(restored.formula_params.real, 0.42)
        self.assertAlmostEqual(restored.formula_params.imag, -0.17)
        self.assertEqual(restored.max_iterations, 640)
        self.assertTrue(restored.is_julia)


@pytest.mark.integration
class TestParamsPanelController(unittest.TestCase):
    def test_controller_operates_on_panel_adapter_without_private_widget_access(
        self,
    ) -> None:
        from fractal_studio.ui.controllers.params_panel_controller import (
            ParamsPanelController,
        )

        class SignalStub:
            def __init__(self) -> None:
                self.emitted: list[object] = []

            def emit(self, *args) -> None:
                self.emitted.append(args[0] if len(args) == 1 else args)

        class ComboStub:
            def __init__(self, items: list[object]) -> None:
                self.items = items
                self.current_index = 0
                self.blocked: list[bool] = []

            def blockSignals(self, blocked: bool) -> None:
                self.blocked.append(blocked)

            def setCurrentIndex(self, index: int) -> None:
                self.current_index = index

            def itemData(self, index: int):
                return self.items[index]

        class SpinStub:
            def __init__(self, value: float) -> None:
                self._value = value

            def setValue(self, value: float) -> None:
                self._value = value

            def value(self) -> float:
                return self._value

        class ToggleStub:
            def __init__(self, checked: bool) -> None:
                self._checked = checked

            def isChecked(self) -> bool:
                return self._checked

            def setChecked(self, checked: bool) -> None:
                self._checked = checked

        class PanelStub:
            _FORMULAS = [
                ("Standard", "standard"),
                ("Multibrot", "multibrot"),
                ("Burning Ship", "burning_ship"),
                ("Tricorn", "tricorn"),
                ("Celtic", "celtic"),
                ("Buffalo", "buffalo"),
                ("Phoenix", "phoenix"),
                ("Newton", "newton"),
            ]

            def __init__(self) -> None:
                self.formula_changed = SignalStub()
                self.mode_changed = SignalStub()
                self.coloring_mode_changed = SignalStub()
                self.power_visibility: list[bool] = []
                self.power_labels: list[str] = []
                self.phoenix_visibility: list[bool] = []
                self.mode_visibility: list[bool] = []
                self.julia_visibility: list[bool] = []
                self.trap_visibility: list[bool] = []
                self._formula_combo = ComboStub(list(range(len(self._FORMULAS))))
                self._mode_combo = ComboStub(["Mandelbrot", "Julia"])
                self._coloring_combo = ComboStub(
                    [
                        "smooth_escape",
                        "orbit_trap_circle",
                        "orbit_trap_cross",
                        "orbit_trap_point",
                    ]
                )
                self._power_spin = SpinStub(0)
                self._phoenix_real_spin = SpinStub(0.0)
                self._phoenix_imag_spin = SpinStub(0.0)
                self._julia_real_spin = SpinStub(0.0)
                self._julia_imag_spin = SpinStub(0.0)
                self._iterations_spin = SpinStub(0)
                self._trap_x_spin = SpinStub(0.0)
                self._trap_y_spin = SpinStub(0.0)
                self._cycle_button = ToggleStub(True)
                self.reset_calls = 0

            def formula_key(self, index: int) -> str:
                return self._FORMULAS[index][1]

            def set_power_visible(self, visible: bool) -> None:
                self.power_visibility.append(visible)

            def set_power_label_text(self, text: str) -> None:
                self.power_labels.append(text)

            def set_phoenix_visible(self, visible: bool) -> None:
                self.phoenix_visibility.append(visible)

            def set_mode_visible(self, visible: bool) -> None:
                self.mode_visibility.append(visible)

            def set_mode_index(self, index: int) -> None:
                self._mode_combo.setCurrentIndex(index)

            def set_julia_visible(self, visible: bool) -> None:
                self.julia_visibility.append(visible)

            def coloring_mode(self, index: int):
                return self._coloring_combo.itemData(index)

            def set_trap_point_visible(self, visible: bool) -> None:
                self.trap_visibility.append(visible)

            def reset_controls(self) -> None:
                self.reset_calls += 1
                self._formula_combo.setCurrentIndex(0)
                self._mode_combo.setCurrentIndex(0)
                self._coloring_combo.setCurrentIndex(0)
                self._power_spin.setValue(3)
                self._phoenix_real_spin.setValue(0.5)
                self._phoenix_imag_spin.setValue(0.0)
                self._julia_real_spin.setValue(-0.8)
                self._julia_imag_spin.setValue(0.156)
                self._iterations_spin.setValue(256)
                self._trap_x_spin.setValue(0.0)
                self._trap_y_spin.setValue(0.0)
                if self._cycle_button.isChecked():
                    self._cycle_button.setChecked(False)

        controller = ParamsPanelController()
        panel = PanelStub()

        formula = controller.handle_formula_changed(panel, 7)
        is_julia = controller.handle_mode_changed(panel, "Julia")
        coloring = controller.handle_coloring_changed(panel, 3)
        controller.reset(panel)

        self.assertEqual(formula, "newton")
        self.assertEqual(panel.formula_changed.emitted, ["newton", "standard"])
        self.assertEqual(panel.power_visibility, [True, False])
        self.assertEqual(panel.power_labels, ["Degree (n):", "Power (n):"])
        self.assertEqual(panel.phoenix_visibility, [False, False])
        self.assertEqual(panel.mode_visibility, [False, True])
        self.assertEqual(panel._mode_combo.current_index, 0)
        self.assertTrue(is_julia)
        self.assertEqual(panel.mode_changed.emitted, [True, False])
        self.assertEqual(panel.julia_visibility, [True, False])
        self.assertEqual(coloring, "orbit_trap_point")
        self.assertEqual(
            panel.coloring_mode_changed.emitted, ["orbit_trap_point", "smooth_escape"]
        )
        self.assertEqual(panel.trap_visibility, [True, False])
        self.assertEqual(panel.reset_calls, 1)
        self.assertEqual(panel._formula_combo.current_index, 0)
        self.assertEqual(panel._mode_combo.current_index, 0)
        self.assertEqual(panel._coloring_combo.current_index, 0)
        self.assertFalse(panel._cycle_button.isChecked())


