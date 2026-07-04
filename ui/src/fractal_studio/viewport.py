from __future__ import annotations

import math

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QMouseEvent, QPainter, QPaintEvent, QWheelEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QWidget,
)

from typing import TYPE_CHECKING

from fractal_studio.backend import Color, CoreBackend
from fractal_studio.ui.controllers.params_panel_controller import ParamsPanelController
from fractal_studio.state import (
    FormulaParams,
    JuliaParams,
    NewtonParams,
    ParamsState,
    PhoenixParams,
    StandardParams,
    ViewportState,
)
from fractal_studio.ui.controllers.viewport_controller import ViewportController

if TYPE_CHECKING:
    from fractal_studio.ui.workers.render_scheduler import RenderScheduler


class FractalViewportWidget(QWidget):
    status_changed = Signal(str)
    scale_changed = Signal(float)

    _ASPECT_RATIOS: dict[str, tuple[int, int]] = {
        "square": (1, 1),
        "portrait": (3, 4),
        "landscape": (4, 3),
    }

    # Default centers per formula (Mandelbrot mode)
    _FORMULA_CENTERS: dict[str, tuple[float, float]] = {
        "standard": (-0.5, 0.0),
        "burning_ship": (-0.5, -0.5),
        "tricorn": (0.0, 0.0),
        "celtic": (-0.5, 0.0),
        "buffalo": (-0.5, -0.5),
        "multibrot": (0.0, 0.0),
        "phoenix": (0.0, 0.0),
        "newton": (0.0, 0.0),
    }

    _NEWTON_SCALE = 2.0

    def __init__(
        self,
        backend: CoreBackend,
        scheduler: RenderScheduler | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._controller = ViewportController(backend, scheduler=scheduler)
        self._palette: list[Color] = []
        self._image: QImage | None = None
        self._formula = "standard"
        self._is_julia = False
        self._julia_real = -0.8
        self._julia_imag = 0.156
        self._power = 3
        self._phoenix_real = 0.5
        self._phoenix_imag = 0.0
        self._center_x = -0.5
        self._center_y = 0.0
        self._scale = 3.0
        self._max_iterations = 256
        self._pan_origin: tuple[float, float] | None = None
        self._pan_center_start: tuple[float, float] = (-0.5, 0.0)
        self._coloring_mode = "smooth_escape"
        self._trap_x = 0.0
        self._trap_y = 0.0
        self._palette_offset = 0.0
        self._aspect_ratio_mode = "square"
        self._cycle_active = False
        self._cycle_timer = QTimer(self)
        self._cycle_timer.setInterval(50)  # 20 fps
        self._cycle_timer.timeout.connect(self._advance_cycle)
        self.setMinimumSize(320, 320)
        size_policy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        size_policy.setHeightForWidth(True)
        self.setSizePolicy(size_policy)

    def hasHeightForWidth(self) -> bool:
        return True

    def set_aspect_ratio_mode(self, mode: str) -> None:
        self._controller.apply_aspect_ratio_mode(self, mode)

    def aspect_ratio_mode(self) -> str:
        return self._aspect_ratio_mode

    def heightForWidth(self, width: int) -> int:
        aspect_width, aspect_height = self._ASPECT_RATIOS[self._aspect_ratio_mode]
        return max(320, round(width * aspect_height / aspect_width))

    def sizeHint(self) -> QSize:
        aspect_width, aspect_height = self._ASPECT_RATIOS[self._aspect_ratio_mode]
        width = 720
        return QSize(width, round(width * aspect_height / aspect_width))

    def set_palette(self, palette: list[Color]) -> None:
        self._controller.set_palette(self, palette)

    def palette(self) -> list[Color]:
        return list(self._palette)

    def replace_palette(self, palette: list[Color]) -> None:
        self._palette = list(palette)

    def supported_aspect_ratio_modes(self) -> set[str]:
        return set(self._ASPECT_RATIOS)

    def load_aspect_ratio_mode(self, mode: str) -> None:
        self._aspect_ratio_mode = mode

    def _current_formula_params(self) -> FormulaParams:
        if self._formula == "phoenix":
            return PhoenixParams(real=self._phoenix_real, imag=self._phoenix_imag)
        if self._formula == "newton":
            return NewtonParams(trap_x=self._trap_x, trap_y=self._trap_y)
        if self._is_julia or self._formula == "julia":
            return JuliaParams(cx=self._julia_real, cy=self._julia_imag)
        return StandardParams()

    def to_state(self) -> ViewportState:
        return ViewportState(
            formula=self._formula,
            center_x=self._center_x,
            center_y=self._center_y,
            scale=self._scale,
            max_iterations=self._max_iterations,
            is_julia=self._is_julia,
            formula_params=self._current_formula_params(),
            power=self._power,
            coloring_mode=self._coloring_mode,
            palette_offset=self._palette_offset,
        )

    def load_state(self, state: ViewportState) -> None:
        self._formula = state.formula
        self._center_x = state.center_x
        self._center_y = state.center_y
        self._scale = state.scale
        self._max_iterations = state.max_iterations
        self._is_julia = state.is_julia
        fp = state.formula_params
        if isinstance(fp, JuliaParams):
            self._julia_real = fp.cx
            self._julia_imag = fp.cy
        elif isinstance(fp, PhoenixParams):
            self._phoenix_real = fp.real
            self._phoenix_imag = fp.imag
        elif isinstance(fp, NewtonParams):
            self._trap_x = fp.trap_x
            self._trap_y = fp.trap_y
        self._power = state.power
        self._coloring_mode = state.coloring_mode
        self._palette_offset = state.palette_offset

    def formula_center(self, formula: str) -> tuple[float, float]:
        return self._FORMULA_CENTERS.get(formula, (-0.5, 0.0))

    def newton_scale(self) -> float:
        return self._NEWTON_SCALE

    def set_cycle_active_flag(self, active: bool) -> None:
        self._cycle_active = active

    def start_cycle_timer(self) -> None:
        self._cycle_timer.start()

    def stop_cycle_timer(self) -> None:
        self._cycle_timer.stop()

    def set_cycle_interval(self, interval: int) -> None:
        self._cycle_timer.setInterval(interval)

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

    def store_rendered_image(self, image: QImage) -> None:
        self._image = image

    def apply_state(
        self, state: ViewportState, *, rerender: bool = True, emit_scale: bool = False
    ) -> None:
        self._controller.apply_state(self, state, rerender=rerender)
        if emit_scale:
            self.scale_changed.emit(self._scale)

    def set_formula(self, formula: str) -> None:
        self._controller.set_formula(self, formula)
        self.scale_changed.emit(self._scale)

    def set_mode(self, is_julia: bool) -> None:
        self._controller.set_mode(self, is_julia)
        self.scale_changed.emit(self._scale)

    def set_power(self, power: int) -> None:
        self._controller.set_power(self, power)

    def set_phoenix_constant(self, real: float, imag: float) -> None:
        self._controller.set_phoenix_constant(self, real, imag)

    def set_scale(self, scale: float) -> None:
        self._controller.set_scale(self, scale)

    def set_julia_constant(self, real: float, imag: float) -> None:
        self._controller.set_julia_constant(self, real, imag)

    def set_max_iterations(self, value: int) -> None:
        self._controller.set_max_iterations(self, value)

    def set_coloring_mode(self, mode: str) -> None:
        self._controller.set_coloring_mode(self, mode)

    def set_trap_point(self, x: float, y: float) -> None:
        self._controller.set_trap_point(self, x, y)

    def set_palette_offset(self, offset: float) -> None:
        self._controller.set_palette_offset(self, offset)

    def set_cycle_active(self, active: bool) -> None:
        self._controller.set_cycle_active(self, active)

    def set_cycle_speed(self, steps_per_second: float) -> None:
        self._controller.set_cycle_speed(self, steps_per_second)

    def _advance_cycle(self) -> None:
        self._controller.advance_cycle(self)

    def request_render(self) -> None:
        self._controller.render(self)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._controller.handle_resize(self):
            self.request_render()

    def wheelEvent(self, event: QWheelEvent) -> None:
        self._controller.handle_wheel(self, event.angleDelta().y())
        self.scale_changed.emit(self._scale)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._controller.handle_mouse_press(
                self, event.position().x(), event.position().y()
            )

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._controller.handle_mouse_double_click(
                self, event.position().x(), event.position().y()
            )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._controller.handle_mouse_move(
            self, event.position().x(), event.position().y()
        ):
            self.request_render()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._controller.handle_mouse_release(self)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        if self._image is not None:
            painter.drawImage(0, 0, self._image)
        elif not self._backend.available:
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Build fractal_core to enable rendering.",
            )


class FractalParamsPanel(QWidget):
    formula_changed = Signal(str)
    mode_changed = Signal(bool)  # True = Julia
    power_changed = Signal(int)
    phoenix_changed = Signal(float, float)
    julia_constant_changed = Signal(float, float)
    max_iterations_changed = Signal(int)
    zoom_changed = Signal(float)  # emits scale value
    coloring_mode_changed = Signal(str)
    trap_point_changed = Signal(float, float)
    cycle_toggled = Signal(bool)
    cycle_speed_changed = Signal(float)

    _DEFAULT_SCALE = 3.0
    _FORMULAS = [
        ("Standard  (z² + c)", "standard"),
        ("Multibrot  (zⁿ + c)", "multibrot"),
        ("Burning Ship", "burning_ship"),
        ("Tricorn", "tricorn"),
        ("Celtic", "celtic"),
        ("Buffalo", "buffalo"),
        ("Phoenix", "phoenix"),
        ("Newton  (zⁿ - 1 = 0)", "newton"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = ParamsPanelController()

        self._formula_combo = QComboBox()
        for label, _ in self._FORMULAS:
            self._formula_combo.addItem(label)

        self._mode_label = QLabel("Mode:")
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Mandelbrot", "Julia"])

        self._power_label = QLabel("Power (n):")
        self._power_spin = QSpinBox()
        self._power_spin.setRange(2, 10)
        self._power_spin.setValue(3)

        self._phoenix_real_label = QLabel("Phoenix p (real):")
        self._phoenix_real_spin = QDoubleSpinBox()
        self._phoenix_real_spin.setRange(-2.0, 2.0)
        self._phoenix_real_spin.setSingleStep(0.05)
        self._phoenix_real_spin.setDecimals(4)
        self._phoenix_real_spin.setValue(0.5)

        self._phoenix_imag_label = QLabel("Phoenix p (imag):")
        self._phoenix_imag_spin = QDoubleSpinBox()
        self._phoenix_imag_spin.setRange(-2.0, 2.0)
        self._phoenix_imag_spin.setSingleStep(0.05)
        self._phoenix_imag_spin.setDecimals(4)
        self._phoenix_imag_spin.setValue(0.0)

        self._julia_real_label = QLabel("Julia real:")
        self._julia_real_spin = QDoubleSpinBox()
        self._julia_real_spin.setRange(-2.0, 2.0)
        self._julia_real_spin.setSingleStep(0.01)
        self._julia_real_spin.setDecimals(4)
        self._julia_real_spin.setValue(-0.8)

        self._julia_imag_label = QLabel("Julia imaginary:")
        self._julia_imag_spin = QDoubleSpinBox()
        self._julia_imag_spin.setRange(-2.0, 2.0)
        self._julia_imag_spin.setSingleStep(0.01)
        self._julia_imag_spin.setDecimals(4)
        self._julia_imag_spin.setValue(0.156)

        self._iterations_spin = QSpinBox()
        self._iterations_spin.setRange(32, 4096)
        self._iterations_spin.setSingleStep(64)
        self._iterations_spin.setValue(256)

        self._zoom_spin = QDoubleSpinBox()
        self._zoom_spin.setRange(0.0, 14.0)
        self._zoom_spin.setSingleStep(0.25)
        self._zoom_spin.setDecimals(2)
        self._zoom_spin.setValue(0.0)
        self._zoom_spin.setToolTip("0 = default view  ·  1 = 10×  ·  2 = 100×  ·  …")

        self._coloring_combo = QComboBox()
        for label, key in [
            ("Smooth Escape", "smooth_escape"),
            ("Orbit Trap: Circle", "orbit_trap_circle"),
            ("Orbit Trap: Cross", "orbit_trap_cross"),
            ("Orbit Trap: Point", "orbit_trap_point"),
            ("Interior Dwell", "interior_dwell"),
        ]:
            self._coloring_combo.addItem(label, key)

        self._trap_x_label = QLabel("Trap X:")
        self._trap_x_spin = QDoubleSpinBox()
        self._trap_x_spin.setRange(-3.0, 3.0)
        self._trap_x_spin.setSingleStep(0.1)
        self._trap_x_spin.setDecimals(3)
        self._trap_x_spin.setValue(0.0)

        self._trap_y_label = QLabel("Trap Y:")
        self._trap_y_spin = QDoubleSpinBox()
        self._trap_y_spin.setRange(-3.0, 3.0)
        self._trap_y_spin.setSingleStep(0.1)
        self._trap_y_spin.setDecimals(3)
        self._trap_y_spin.setValue(0.0)

        self._cycle_button = QPushButton("▶ Cycle")
        self._cycle_button.setCheckable(True)
        self._cycle_speed_spin = QDoubleSpinBox()
        self._cycle_speed_spin.setRange(0.5, 60.0)
        self._cycle_speed_spin.setSingleStep(0.5)
        self._cycle_speed_spin.setDecimals(1)
        self._cycle_speed_spin.setValue(10.0)
        self._cycle_speed_spin.setSuffix(" fps")

        cycle_row = QWidget()
        cycle_layout = QHBoxLayout()
        cycle_layout.setContentsMargins(0, 0, 0, 0)
        cycle_layout.addWidget(self._cycle_button)
        cycle_layout.addWidget(self._cycle_speed_spin)
        cycle_row.setLayout(cycle_layout)

        form = QFormLayout()
        form.addRow("Formula:", self._formula_combo)
        form.addRow(self._mode_label, self._mode_combo)
        form.addRow(self._power_label, self._power_spin)
        form.addRow(self._phoenix_real_label, self._phoenix_real_spin)
        form.addRow(self._phoenix_imag_label, self._phoenix_imag_spin)
        form.addRow(self._julia_real_label, self._julia_real_spin)
        form.addRow(self._julia_imag_label, self._julia_imag_spin)
        form.addRow("Max iterations:", self._iterations_spin)
        form.addRow("Zoom (log₁₀):", self._zoom_spin)
        form.addRow("Coloring:", self._coloring_combo)
        form.addRow(self._trap_x_label, self._trap_x_spin)
        form.addRow(self._trap_y_label, self._trap_y_spin)
        form.addRow("Color cycle:", cycle_row)

        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self.reset)
        form.addRow(reset_button)

        self.setLayout(form)

        self._formula_combo.currentIndexChanged.connect(self._on_formula_changed)
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self._power_spin.valueChanged.connect(self.power_changed)
        self._phoenix_real_spin.valueChanged.connect(self._on_phoenix_changed)
        self._phoenix_imag_spin.valueChanged.connect(self._on_phoenix_changed)
        self._julia_real_spin.valueChanged.connect(self._on_julia_changed)
        self._julia_imag_spin.valueChanged.connect(self._on_julia_changed)
        self._iterations_spin.valueChanged.connect(self.max_iterations_changed)
        self._zoom_spin.valueChanged.connect(self._on_zoom_changed)
        self._coloring_combo.currentIndexChanged.connect(self._on_coloring_changed)
        self._trap_x_spin.valueChanged.connect(self._on_trap_changed)
        self._trap_y_spin.valueChanged.connect(self._on_trap_changed)
        self._cycle_button.toggled.connect(self.cycle_toggled)
        self._cycle_speed_spin.valueChanged.connect(self.cycle_speed_changed)

        self._set_power_visible(False)
        self._set_phoenix_visible(False)
        self._set_julia_visible(False)
        self._set_trap_point_visible(False)

    def set_scale(self, scale: float) -> None:
        depth = math.log10(self._DEFAULT_SCALE / max(scale, 1e-14))
        self._zoom_spin.blockSignals(True)
        self._zoom_spin.setValue(round(max(0.0, min(14.0, depth)), 2))
        self._zoom_spin.blockSignals(False)

    def to_state(self) -> ParamsState:
        formula = self._FORMULAS[self._formula_combo.currentIndex()][1]
        coloring_mode = self._coloring_combo.currentData()
        is_julia = self._mode_combo.currentIndex() == 1

        if formula == "phoenix":
            formula_params: FormulaParams = PhoenixParams(
                real=self._phoenix_real_spin.value(),
                imag=self._phoenix_imag_spin.value(),
            )
        elif formula == "newton":
            formula_params = NewtonParams(
                trap_x=self._trap_x_spin.value(),
                trap_y=self._trap_y_spin.value(),
            )
        elif is_julia or formula == "julia":
            formula_params = JuliaParams(
                cx=self._julia_real_spin.value(),
                cy=self._julia_imag_spin.value(),
            )
        else:
            formula_params = StandardParams()

        return ParamsState(
            formula=formula,
            is_julia=is_julia,
            power=self._power_spin.value(),
            formula_params=formula_params,
            max_iterations=self._iterations_spin.value(),
            scale=self._DEFAULT_SCALE / (10.0 ** self._zoom_spin.value()),
            coloring_mode=str(coloring_mode)
            if coloring_mode is not None
            else "smooth_escape",
            cycle_active=self._cycle_button.isChecked(),
            cycle_speed=self._cycle_speed_spin.value(),
        )

    def apply_state(self, state: ParamsState | ViewportState) -> None:
        params_state = (
            state
            if isinstance(state, ParamsState)
            else ParamsState.from_viewport_state(
                state,
                cycle_active=self._cycle_button.isChecked(),
                cycle_speed=self._cycle_speed_spin.value(),
            )
        )

        widgets = [
            self._formula_combo,
            self._mode_combo,
            self._power_spin,
            self._phoenix_real_spin,
            self._phoenix_imag_spin,
            self._julia_real_spin,
            self._julia_imag_spin,
            self._iterations_spin,
            self._coloring_combo,
            self._trap_x_spin,
            self._trap_y_spin,
            self._cycle_button,
            self._cycle_speed_spin,
        ]
        for widget in widgets:
            widget.blockSignals(True)

        try:
            formula_index = 0
            for idx, (_, key) in enumerate(self._FORMULAS):
                if key == params_state.formula:
                    formula_index = idx
                    break

            self._formula_combo.setCurrentIndex(formula_index)
            self._set_power_visible(params_state.formula in ("multibrot", "newton"))
            self._power_label.setText(
                "Degree (n):" if params_state.formula == "newton" else "Power (n):"
            )
            self._set_phoenix_visible(params_state.formula == "phoenix")
            self._set_mode_visible(params_state.formula != "newton")

            self._mode_combo.setCurrentIndex(1 if params_state.is_julia else 0)
            self._set_julia_visible(params_state.is_julia)
            self._power_spin.setValue(params_state.power)

            fp = params_state.formula_params
            if isinstance(fp, PhoenixParams):
                self._phoenix_real_spin.setValue(fp.real)
                self._phoenix_imag_spin.setValue(fp.imag)
            if isinstance(fp, JuliaParams):
                self._julia_real_spin.setValue(fp.cx)
                self._julia_imag_spin.setValue(fp.cy)
            self._iterations_spin.setValue(params_state.max_iterations)

            color_index = self._coloring_combo.findData(params_state.coloring_mode)
            self._coloring_combo.setCurrentIndex(max(0, color_index))
            self._set_trap_point_visible(
                params_state.coloring_mode == "orbit_trap_point"
            )
            if isinstance(fp, NewtonParams):
                self._trap_x_spin.setValue(fp.trap_x)
                self._trap_y_spin.setValue(fp.trap_y)

            self._cycle_button.setChecked(params_state.cycle_active)
            self._cycle_speed_spin.setValue(params_state.cycle_speed)
            self.set_scale(params_state.scale)
        finally:
            for widget in widgets:
                widget.blockSignals(False)

    def reset(self) -> None:
        self._controller.reset(self)

    def formula_key(self, index: int) -> str:
        return self._FORMULAS[index][1]

    def set_power_visible(self, visible: bool) -> None:
        self._set_power_visible(visible)

    def set_power_label_text(self, text: str) -> None:
        self._power_label.setText(text)

    def set_phoenix_visible(self, visible: bool) -> None:
        self._set_phoenix_visible(visible)

    def set_mode_visible(self, visible: bool) -> None:
        self._set_mode_visible(visible)

    def set_mode_index(self, index: int) -> None:
        self._mode_combo.setCurrentIndex(index)

    def set_julia_visible(self, visible: bool) -> None:
        self._set_julia_visible(visible)

    def coloring_mode(self, index: int):
        return self._coloring_combo.itemData(index)

    def set_trap_point_visible(self, visible: bool) -> None:
        self._set_trap_point_visible(visible)

    def reset_controls(self) -> None:
        for combo in (self._formula_combo, self._mode_combo, self._coloring_combo):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

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

    def _on_formula_changed(self, index: int) -> None:
        self._controller.handle_formula_changed(self, index)

    def _on_phoenix_changed(self) -> None:
        self.phoenix_changed.emit(
            self._phoenix_real_spin.value(),
            self._phoenix_imag_spin.value(),
        )

    def _on_mode_changed(self, text: str) -> None:
        self._controller.handle_mode_changed(self, text)

    def _on_julia_changed(self) -> None:
        self.julia_constant_changed.emit(
            self._julia_real_spin.value(),
            self._julia_imag_spin.value(),
        )

    def _on_zoom_changed(self, depth: float) -> None:
        self.zoom_changed.emit(self._controller.zoom_scale(self._DEFAULT_SCALE, depth))

    def _set_power_visible(self, visible: bool) -> None:
        self._power_label.setVisible(visible)
        self._power_spin.setVisible(visible)

    def _set_phoenix_visible(self, visible: bool) -> None:
        self._phoenix_real_label.setVisible(visible)
        self._phoenix_real_spin.setVisible(visible)
        self._phoenix_imag_label.setVisible(visible)
        self._phoenix_imag_spin.setVisible(visible)

    def _set_mode_visible(self, visible: bool) -> None:
        self._mode_label.setVisible(visible)
        self._mode_combo.setVisible(visible)

    def _set_julia_visible(self, visible: bool) -> None:
        self._julia_real_label.setVisible(visible)
        self._julia_real_spin.setVisible(visible)
        self._julia_imag_label.setVisible(visible)
        self._julia_imag_spin.setVisible(visible)

    def _on_coloring_changed(self, index: int) -> None:
        self._controller.handle_coloring_changed(self, index)

    def _on_trap_changed(self) -> None:
        self.trap_point_changed.emit(
            self._trap_x_spin.value(), self._trap_y_spin.value()
        )

    def _set_trap_point_visible(self, visible: bool) -> None:
        self._trap_x_label.setVisible(visible)
        self._trap_x_spin.setVisible(visible)
        self._trap_y_label.setVisible(visible)
        self._trap_y_spin.setVisible(visible)
