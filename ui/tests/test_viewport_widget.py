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
class TestViewportRenderScheduling(QtWindowTestCase):
    def test_mouse_move_delegates_each_render_request(self) -> None:
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from fractal_studio.backend import CoreBackend
        from fractal_studio.viewport import FractalViewportWidget

        class ControllerStub:
            def __init__(self) -> None:
                self.move_calls = 0
                self.render_calls = 0

            def handle_mouse_move(self, widget, x: float, y: float) -> bool:
                self.move_calls += 1
                return True

            def render(self, widget) -> None:
                self.render_calls += 1

        widget = FractalViewportWidget(CoreBackend(None))
        self.addCleanup(widget.deleteLater)
        stub = ControllerStub()
        widget._controller = stub

        for _ in range(5):
            event = QMouseEvent(
                QEvent.Type.MouseMove,
                QPointF(10.0, 10.0),
                QPointF(10.0, 10.0),
                QPointF(10.0, 10.0),
                Qt.MouseButton.NoButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            widget.mouseMoveEvent(event)

        self.assertEqual(stub.move_calls, 5)
        # request_render delegates synchronously now; coalescing is owned by
        # RenderScheduler (50 ms debounce + generation counter — covered in
        # test_render_workers.py), not by the widget.
        self.assertEqual(stub.render_calls, 5)

    def test_mouse_move_without_pan_does_not_schedule_render(self) -> None:
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from fractal_studio.backend import CoreBackend
        from fractal_studio.viewport import FractalViewportWidget

        class ControllerStub:
            def __init__(self) -> None:
                self.move_calls = 0
                self.render_calls = 0

            def handle_mouse_move(self, widget, x: float, y: float) -> bool:
                self.move_calls += 1
                return False

            def render(self, widget) -> None:
                self.render_calls += 1

        widget = FractalViewportWidget(CoreBackend(None))
        self.addCleanup(widget.deleteLater)
        stub = ControllerStub()
        widget._controller = stub

        event = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(10.0, 10.0),
            QPointF(10.0, 10.0),
            QPointF(10.0, 10.0),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.mouseMoveEvent(event)
        get_app().processEvents()

        self.assertEqual(stub.move_calls, 1)
        self.assertEqual(stub.render_calls, 0)

    def test_resize_delegates_each_render_request(self) -> None:
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QResizeEvent
        from fractal_studio.backend import CoreBackend
        from fractal_studio.viewport import FractalViewportWidget

        class ControllerStub:
            def __init__(self) -> None:
                self.resize_calls = 0
                self.render_calls = 0

            def handle_resize(self, widget) -> bool:
                self.resize_calls += 1
                return True

            def render(self, widget) -> None:
                self.render_calls += 1

        widget = FractalViewportWidget(CoreBackend(None))
        self.addCleanup(widget.deleteLater)
        stub = ControllerStub()
        widget._controller = stub

        for _ in range(5):
            widget.resizeEvent(QResizeEvent(QSize(420, 300), QSize(320, 320)))

        self.assertEqual(stub.resize_calls, 5)
        # Synchronous delegation per event; scheduler owns coalescing.
        self.assertEqual(stub.render_calls, 5)

    def test_resize_without_render_request_does_not_schedule_render(self) -> None:
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QResizeEvent
        from fractal_studio.backend import CoreBackend
        from fractal_studio.viewport import FractalViewportWidget

        class ControllerStub:
            def __init__(self) -> None:
                self.resize_calls = 0
                self.render_calls = 0

            def handle_resize(self, widget) -> bool:
                self.resize_calls += 1
                return False

            def render(self, widget) -> None:
                self.render_calls += 1

        widget = FractalViewportWidget(CoreBackend(None))
        self.addCleanup(widget.deleteLater)
        stub = ControllerStub()
        widget._controller = stub

        widget.resizeEvent(QResizeEvent(QSize(420, 300), QSize(320, 320)))
        get_app().processEvents()

        self.assertEqual(stub.resize_calls, 1)
        self.assertEqual(stub.render_calls, 0)


@pytest.mark.integration
class TestViewportController(unittest.TestCase):
    def test_controller_state_methods_operate_on_viewport_adapter_without_private_widget_access(
        self,
    ) -> None:
        from fractal_studio.state import ViewportState
        from fractal_studio.ui.controllers.viewport_controller import (
            ViewportController,
            ViewportRenderResult,
        )

        class DummyBackend:
            available = False

        class ViewportStub:
            def __init__(self) -> None:
                from fractal_studio.state import StandardParams
                self._state = ViewportState(
                    formula="standard",
                    center_x=-0.5,
                    center_y=0.0,
                    scale=3.0,
                    max_iterations=256,
                    is_julia=False,
                    formula_params=StandardParams(),
                    power=3,
                    coloring_mode="smooth_escape",
                    palette_offset=0.0,
                )
                self._aspect_ratio_mode = "square"
                self.minimum_sizes: list[tuple[int, int]] = []
                self.geometry_updates = 0
                self.repaint_requests = 0
                self.cycle_started = 0
                self.cycle_stopped = 0
                self.cycle_interval = 50
                self.cycle_active = False
                self._pan_origin: tuple[float, float] | None = None
                self._pan_center_start: tuple[float, float] = (-0.5, 0.0)
                self.width_value = 640
                self.height_value = 320

            def supported_aspect_ratio_modes(self) -> set[str]:
                return {"square", "portrait", "landscape"}

            def aspect_ratio_mode(self) -> str:
                return self._aspect_ratio_mode

            def load_aspect_ratio_mode(self, mode: str) -> None:
                self._aspect_ratio_mode = mode

            def heightForWidth(self, width: int) -> int:
                return {"square": width, "portrait": 427, "landscape": 240}[
                    self._aspect_ratio_mode
                ]

            def setMinimumSize(self, width: int, height: int) -> None:
                self.minimum_sizes.append((width, height))

            def updateGeometry(self) -> None:
                self.geometry_updates += 1

            def update(self) -> None:
                self.repaint_requests += 1

            def to_state(self) -> ViewportState:
                return self._state

            def load_state(self, state: ViewportState) -> None:
                self._state = state

            def formula_center(self, formula: str) -> tuple[float, float]:
                return {
                    "standard": (-0.5, 0.0),
                    "multibrot": (0.0, 0.0),
                    "phoenix": (0.0, 0.0),
                    "newton": (0.0, 0.0),
                }.get(formula, (-0.5, 0.0))

            def newton_scale(self) -> float:
                return 2.0

            def set_cycle_active_flag(self, active: bool) -> None:
                self.cycle_active = active

            def start_cycle_timer(self) -> None:
                self.cycle_started += 1

            def stop_cycle_timer(self) -> None:
                self.cycle_stopped += 1

            def set_cycle_interval(self, interval: int) -> None:
                self.cycle_interval = interval

            def set_pan_anchor(
                self, origin: tuple[float, float], center_start: tuple[float, float]
            ) -> None:
                self._pan_origin = origin
                self._pan_center_start = center_start

            def pan_origin(self) -> tuple[float, float] | None:
                return self._pan_origin

            def pan_center_start(self) -> tuple[float, float]:
                return self._pan_center_start

            def clear_pan_anchor(self) -> None:
                self._pan_origin = None

            def width(self) -> int:
                return self.width_value

            def height(self) -> int:
                return self.height_value

        class RecordingViewportController(ViewportController):
            def __init__(self) -> None:
                super().__init__(DummyBackend())
                self.render_count = 0

            def render(self, widget) -> ViewportRenderResult:
                self.render_count += 1
                return ViewportRenderResult(image=None, status=None)

        controller = RecordingViewportController()
        viewport = ViewportStub()

        self.assertEqual(
            controller.apply_aspect_ratio_mode(viewport, "portrait"), "portrait"
        )
        self.assertEqual(viewport.aspect_ratio_mode(), "portrait")
        self.assertEqual(viewport.minimum_sizes[-1], (320, 427))

        controller.apply_state(
            viewport,
            replace(
                viewport.to_state(),
                formula="multibrot",
                scale=0.0,
                max_iterations=0,
                power=1,
                palette_offset=1.25,
            ),
            rerender=False,
        )
        state_after_apply = viewport.to_state()
        self.assertEqual(state_after_apply.formula, "multibrot")
        self.assertEqual(state_after_apply.scale, 1e-12)
        self.assertEqual(state_after_apply.max_iterations, 1)
        self.assertEqual(state_after_apply.power, 2)
        self.assertEqual(state_after_apply.palette_offset, 0.25)

        self.assertEqual(controller.set_formula(viewport, "newton"), 2.0)
        state_after_formula = viewport.to_state()
        self.assertEqual(state_after_formula.formula, "newton")
        self.assertFalse(state_after_formula.is_julia)
        self.assertEqual(
            (state_after_formula.center_x, state_after_formula.center_y), (0.0, 0.0)
        )

        self.assertEqual(controller.set_mode(viewport, True), 3.0)
        state_after_mode = viewport.to_state()
        self.assertTrue(state_after_mode.is_julia)
        self.assertEqual(
            (state_after_mode.center_x, state_after_mode.center_y), (0.0, 0.0)
        )

        from fractal_studio.state import JuliaParams, NewtonParams, PhoenixParams

        controller.set_power(viewport, 4)
        controller.set_phoenix_constant(viewport, 0.2, -0.3)
        self.assertEqual(viewport.to_state().formula_params, PhoenixParams(real=0.2, imag=-0.3))
        controller.set_scale(viewport, 0.5)
        controller.set_julia_constant(viewport, -0.2, 0.4)
        self.assertEqual(viewport.to_state().formula_params, JuliaParams(cx=-0.2, cy=0.4))
        controller.set_max_iterations(viewport, 900)
        controller.set_coloring_mode(viewport, "orbit_trap_point")
        controller.set_trap_point(viewport, 0.25, -0.5)
        controller.set_palette_offset(viewport, 1.75)
        controller.set_cycle_active(viewport, True)
        controller.set_cycle_speed(viewport, 25.0)
        controller.advance_cycle(viewport)
        wheel_scale = controller.handle_wheel(viewport, 120)
        controller.handle_mouse_press(viewport, 100.0, 80.0)
        controller.handle_mouse_move(viewport, 140.0, 100.0)
        controller.handle_mouse_double_click(viewport, 320.0, 160.0)
        controller.handle_mouse_release(viewport)

        final_state = viewport.to_state()
        self.assertEqual(final_state.power, 4)
        self.assertEqual(final_state.max_iterations, 900)
        self.assertEqual(final_state.coloring_mode, "orbit_trap_point")
        self.assertEqual(final_state.formula_params, NewtonParams(trap_x=0.25, trap_y=-0.5))
        self.assertAlmostEqual(final_state.palette_offset, 0.755)
        self.assertAlmostEqual(wheel_scale, final_state.scale)
        self.assertEqual(viewport.cycle_active, True)
        self.assertEqual(viewport.cycle_started, 1)
        self.assertEqual(viewport.cycle_stopped, 0)
        self.assertEqual(viewport.cycle_interval, 40)
        self.assertIsNone(viewport.pan_origin())
        self.assertGreater(controller.render_count, 0)

    def test_controller_render_bridge_uses_viewport_adapter_surface(self) -> None:
        from fractal_studio.backend import CoreBackend
        from fractal_studio.state import ViewportState
        from fractal_studio.ui.controllers.viewport_controller import ViewportController

        class RecordingRenderModule:
            # Fakes the fractal_core module so the real CoreBackend.render
            # unpacking stays under test (render() consumes RenderRequest now).
            def render_fractal(self, formula: str, width: int, height: int, **kwargs):
                self.last_call = {
                    "formula": formula,
                    "width": width,
                    "height": height,
                    **kwargs,
                }
                return bytes([10, 20, 30, 255]) * (width * height)

        class SignalStub:
            def __init__(self) -> None:
                self.emitted: list[str] = []

            def emit(self, value: str) -> None:
                self.emitted.append(value)

        class ViewportRenderStub:
            def __init__(self) -> None:
                from fractal_studio.state import JuliaParams
                self._state = ViewportState(
                    formula="multibrot",
                    center_x=-0.25,
                    center_y=0.5,
                    scale=0.125,
                    max_iterations=512,
                    is_julia=True,
                    formula_params=JuliaParams(cx=-0.8, cy=0.156),
                    power=5,
                    coloring_mode="orbit_trap_point",
                    palette_offset=0.5,
                )
                self._palette = [(1, 2, 3)]
                self.status_changed = SignalStub()
                self.rendered_image = None
                self.updates = 0

            def replace_palette(self, palette) -> None:
                self._palette = list(palette)

            def palette(self):
                return list(self._palette)

            def to_state(self) -> ViewportState:
                return self._state

            def width(self) -> int:
                return 2

            def height(self) -> int:
                return 2

            def store_rendered_image(self, image) -> None:
                self.rendered_image = image

            def update(self) -> None:
                self.updates += 1

        module = RecordingRenderModule()
        backend = CoreBackend(module)
        controller = ViewportController(backend)
        viewport = ViewportRenderStub()

        controller.set_palette(viewport, [(9, 8, 7)])
        result = controller.render(viewport)

        self.assertEqual(viewport.palette(), [(9, 8, 7)])
        self.assertIsNotNone(result.image)
        self.assertIs(viewport.rendered_image, result.image)
        self.assertEqual(viewport.updates, 2)
        self.assertEqual(len(viewport.status_changed.emitted), 2)
        self.assertIn("Multibrot", viewport.status_changed.emitted[-1])
        self.assertEqual(module.last_call["palette"], [(9, 8, 7)])


@pytest.mark.integration
class TestViewportSizing(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_app()

    def test_viewport_prefers_square_shape(self) -> None:
        from fractal_studio.backend import load_backend
        from fractal_studio.viewport import FractalViewportWidget
        from PySide6.QtWidgets import QSizePolicy

        viewport = FractalViewportWidget(load_backend())
        self.assertTrue(viewport.hasHeightForWidth())
        self.assertEqual(viewport.heightForWidth(640), 640)
        self.assertEqual(viewport.sizeHint().width(), viewport.sizeHint().height())
        self.assertEqual(
            viewport.sizePolicy().verticalPolicy(), QSizePolicy.Policy.Fixed
        )

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

        from fractal_studio.state import JuliaParams
        viewport = FractalViewportWidget(load_backend())
        state = ViewportState(
            formula="multibrot",
            center_x=-0.123,
            center_y=0.456,
            scale=0.0025,
            max_iterations=700,
            is_julia=True,
            formula_params=JuliaParams(cx=-0.81, cy=0.156),
            power=5,
            coloring_mode="orbit_trap_cross",
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


@pytest.mark.integration
class TestViewportHints(QtWindowTestCase):
    def test_hint_mentions_double_click_recenter(self) -> None:
        w = self.make_window()
        self.assertIsNotNone(w.viewport_hint_label)
        self.assertIn("double-click", w.viewport_hint_label.text().lower())
        self.assertIn("recenter", w.viewport_hint_label.text().lower())

    def test_main_window_hides_internal_section_state_attributes(self) -> None:
        w = self.make_window()

        with self.assertRaises(AttributeError):
            _ = w.selected_row


