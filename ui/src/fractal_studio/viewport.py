from __future__ import annotations

import math

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QMouseEvent, QPainter, QPaintEvent, QWheelEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QWidget,
)

from fractal_studio.backend import Color, CoreBackend


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
        "standard":     (-0.5,  0.0),
        "burning_ship": (-0.5, -0.5),
        "tricorn":      ( 0.0,  0.0),
        "celtic":       (-0.5,  0.0),
        "buffalo":      (-0.5, -0.5),
        "multibrot":    ( 0.0,  0.0),
        "phoenix":      ( 0.0,  0.0),
        "newton":       ( 0.0,  0.0),
    }

    _NEWTON_SCALE = 2.0

    def __init__(self, backend: CoreBackend, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
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
        size_policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        size_policy.setHeightForWidth(True)
        self.setSizePolicy(size_policy)

    def hasHeightForWidth(self) -> bool:
        return True

    def set_aspect_ratio_mode(self, mode: str) -> None:
        if mode not in self._ASPECT_RATIOS:
            mode = "square"
        if mode == self._aspect_ratio_mode:
            return

        self._aspect_ratio_mode = mode
        self.setMinimumSize(320, self.heightForWidth(320))
        self.updateGeometry()
        self.update()

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
        self._palette = list(palette)
        self._rerender()

    def set_formula(self, formula: str) -> None:
        self._formula = formula
        if formula == "newton":
            self._is_julia = False
        cx, cy = self._FORMULA_CENTERS.get(formula, (-0.5, 0.0)) if not self._is_julia else (0.0, 0.0)
        default_scale = self._NEWTON_SCALE if formula == "newton" else 3.0
        self._center_x, self._center_y, self._scale = cx, cy, default_scale
        self._rerender()
        self.scale_changed.emit(self._scale)

    def set_mode(self, is_julia: bool) -> None:
        self._is_julia = is_julia
        self._center_x = 0.0 if is_julia else self._FORMULA_CENTERS.get(self._formula, (-0.5, 0.0))[0]
        self._center_y = 0.0 if is_julia else self._FORMULA_CENTERS.get(self._formula, (-0.5, 0.0))[1]
        self._scale = 3.0
        self._rerender()
        self.scale_changed.emit(self._scale)

    def set_power(self, power: int) -> None:
        self._power = power
        if self._formula in ("multibrot", "newton"):
            self._rerender()

    def set_phoenix_constant(self, real: float, imag: float) -> None:
        self._phoenix_real = real
        self._phoenix_imag = imag
        if self._formula == "phoenix":
            self._rerender()

    def set_scale(self, scale: float) -> None:
        self._scale = max(1e-12, scale)
        self._rerender()

    def set_julia_constant(self, real: float, imag: float) -> None:
        self._julia_real = real
        self._julia_imag = imag
        if self._is_julia:
            self._rerender()

    def set_max_iterations(self, value: int) -> None:
        self._max_iterations = value
        self._rerender()

    def set_coloring_mode(self, mode: str) -> None:
        self._coloring_mode = mode
        self._rerender()

    def set_trap_point(self, x: float, y: float) -> None:
        self._trap_x = x
        self._trap_y = y
        if self._coloring_mode == "orbit_trap_point":
            self._rerender()

    def set_palette_offset(self, offset: float) -> None:
        self._palette_offset = offset % 1.0
        self._rerender()

    def set_cycle_active(self, active: bool) -> None:
        self._cycle_active = active
        if active:
            self._cycle_timer.start()
        else:
            self._cycle_timer.stop()

    def set_cycle_speed(self, steps_per_second: float) -> None:
        interval = max(16, int(1000.0 / max(steps_per_second, 0.1)))
        self._cycle_timer.setInterval(interval)

    def _advance_cycle(self) -> None:
        self._palette_offset = (self._palette_offset + 0.005) % 1.0
        self._rerender()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._rerender()

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 0.85 if event.angleDelta().y() > 0 else 1.0 / 0.85
        self._scale = max(1e-12, self._scale * factor)
        self._rerender()
        self.scale_changed.emit(self._scale)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pan_origin = (event.position().x(), event.position().y())
            self._pan_center_start = (self._center_x, self._center_y)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pan_origin = None  # cancel any pan state the initial press started
            aspect = self.width() / max(1, self.height())
            self._center_x += (event.position().x() / self.width() - 0.5) * self._scale * aspect
            self._center_y += (0.5 - event.position().y() / self.height()) * self._scale
            self._rerender()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan_origin is None:
            return
        dx = event.position().x() - self._pan_origin[0]
        dy = event.position().y() - self._pan_origin[1]
        aspect = self.width() / max(1, self.height())
        self._center_x = self._pan_center_start[0] - dx / self.width() * self._scale * aspect
        self._center_y = self._pan_center_start[1] + dy / self.height() * self._scale
        self._rerender()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pan_origin = None

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

    def _rerender(self) -> None:
        if not self._backend.available or not self._palette:
            return
        w = max(1, self.width())
        h = max(1, self.height())
        raw = self._backend.render_fractal(
            self._formula, w, h,
            is_julia=self._is_julia,
            julia_real=self._julia_real,
            julia_imag=self._julia_imag,
            power=self._power,
            phoenix_real=self._phoenix_real,
            phoenix_imag=self._phoenix_imag,
            center_x=self._center_x,
            center_y=self._center_y,
            scale=self._scale,
            max_iterations=self._max_iterations,
            palette=self._palette,
            coloring_mode=self._coloring_mode,
            trap_x=self._trap_x,
            trap_y=self._trap_y,
            palette_offset=self._palette_offset,
        )
        img = QImage(raw, w, h, w * 4, QImage.Format.Format_RGBA8888)
        self._image = img.copy()
        self.update()
        label = self._formula.replace("_", " ").title()
        mode = "Julia" if self._is_julia else "Mandelbrot"
        extra = f" (n={self._power})" if self._formula == "multibrot" else ""
        self.status_changed.emit(
            f"{label}{extra} · {mode} | "
            f"center ({self._center_x:.4f}, {self._center_y:.4f}) | "
            f"scale {self._scale:.4g} | "
            f"{self._max_iterations} iters"
        )


class FractalParamsPanel(QGroupBox):
    formula_changed = Signal(str)
    mode_changed = Signal(bool)   # True = Julia
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
        ("Standard  (z² + c)",  "standard"),
        ("Burning Ship",         "burning_ship"),
        ("Tricorn",              "tricorn"),
        ("Celtic",               "celtic"),
        ("Buffalo",              "buffalo"),
        ("Multibrot  (zⁿ + c)", "multibrot"),
        ("Phoenix",              "phoenix"),
        ("Newton  (zⁿ - 1 = 0)", "newton"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Fractal Parameters")

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
            ("Smooth Escape",       "smooth_escape"),
            ("Orbit Trap: Circle",  "orbit_trap_circle"),
            ("Orbit Trap: Cross",   "orbit_trap_cross"),
            ("Orbit Trap: Point",   "orbit_trap_point"),
            ("Interior Dwell",      "interior_dwell"),
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

    def reset(self) -> None:
        for combo, handler in (
            (self._formula_combo, lambda: self._on_formula_changed(0)),
            (self._mode_combo,    lambda: self._on_mode_changed("Mandelbrot")),
            (self._coloring_combo,lambda: self._on_coloring_changed(0)),
        ):
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

        # Call handlers explicitly so they always fire regardless of prior state.
        # formula handler resets center + scale in the viewport.
        self._on_formula_changed(0)
        self._on_mode_changed("Mandelbrot")
        self._on_coloring_changed(0)

    def _on_formula_changed(self, index: int) -> None:
        formula = self._FORMULAS[index][1]
        is_newton = formula == "newton"
        self._set_power_visible(formula in ("multibrot", "newton"))
        self._power_label.setText("Degree (n):" if is_newton else "Power (n):")
        self._set_phoenix_visible(formula == "phoenix")
        self._set_mode_visible(not is_newton)
        if is_newton:
            self._mode_combo.setCurrentIndex(0)
        self.formula_changed.emit(formula)

    def _on_phoenix_changed(self) -> None:
        self.phoenix_changed.emit(
            self._phoenix_real_spin.value(),
            self._phoenix_imag_spin.value(),
        )

    def _on_mode_changed(self, text: str) -> None:
        is_julia = text == "Julia"
        self._set_julia_visible(is_julia)
        self.mode_changed.emit(is_julia)

    def _on_julia_changed(self) -> None:
        self.julia_constant_changed.emit(
            self._julia_real_spin.value(),
            self._julia_imag_spin.value(),
        )

    def _on_zoom_changed(self, depth: float) -> None:
        self.zoom_changed.emit(self._DEFAULT_SCALE / (10.0 ** depth))

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
        mode = self._coloring_combo.itemData(index)
        self._set_trap_point_visible(mode == "orbit_trap_point")
        self.coloring_mode_changed.emit(mode)

    def _on_trap_changed(self) -> None:
        self.trap_point_changed.emit(self._trap_x_spin.value(), self._trap_y_spin.value())

    def _set_trap_point_visible(self, visible: bool) -> None:
        self._trap_x_label.setVisible(visible)
        self._trap_x_spin.setVisible(visible)
        self._trap_y_label.setVisible(visible)
        self._trap_y_spin.setVisible(visible)
