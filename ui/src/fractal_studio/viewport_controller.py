from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage

from fractal_studio.backend import Color, CoreBackend
from fractal_studio.state import ViewportState

if TYPE_CHECKING:
    from fractal_studio.viewport import FractalViewportWidget


@dataclass(frozen=True)
class ViewportRenderResult:
    image: QImage | None
    status: str | None


class ViewportController:
    def __init__(self, backend: CoreBackend) -> None:
        self._backend = backend

    def apply_aspect_ratio_mode(self, widget: FractalViewportWidget, mode: str) -> str:
        if mode not in widget._ASPECT_RATIOS:
            mode = "square"
        if mode == widget._aspect_ratio_mode:
            return mode

        widget._aspect_ratio_mode = mode
        widget.setMinimumSize(320, widget.heightForWidth(320))
        widget.updateGeometry()
        widget.update()
        return mode

    def set_palette(self, widget: FractalViewportWidget, palette: list[Color]) -> None:
        widget._palette = list(palette)
        self.render(widget)

    def apply_state(self, widget: FractalViewportWidget, state: ViewportState, *, rerender: bool = True) -> None:
        widget._formula = state.formula
        widget._center_x = state.center_x
        widget._center_y = state.center_y
        widget._scale = max(1e-12, state.scale)
        widget._max_iterations = max(1, state.max_iterations)
        widget._is_julia = bool(state.is_julia)
        widget._julia_real = state.julia_real
        widget._julia_imag = state.julia_imag
        widget._power = max(2, state.power)
        widget._phoenix_real = state.phoenix_real
        widget._phoenix_imag = state.phoenix_imag
        widget._coloring_mode = state.coloring_mode
        widget._trap_x = state.trap_x
        widget._trap_y = state.trap_y
        widget._palette_offset = state.palette_offset % 1.0

        if rerender:
            self.render(widget)

    def set_formula(self, widget: FractalViewportWidget, formula: str) -> float:
        widget._formula = formula
        if formula == "newton":
            widget._is_julia = False
        cx, cy = widget._FORMULA_CENTERS.get(formula, (-0.5, 0.0)) if not widget._is_julia else (0.0, 0.0)
        default_scale = widget._NEWTON_SCALE if formula == "newton" else 3.0
        widget._center_x, widget._center_y, widget._scale = cx, cy, default_scale
        self.render(widget)
        return widget._scale

    def set_mode(self, widget: FractalViewportWidget, is_julia: bool) -> float:
        widget._is_julia = is_julia
        widget._center_x = 0.0 if is_julia else widget._FORMULA_CENTERS.get(widget._formula, (-0.5, 0.0))[0]
        widget._center_y = 0.0 if is_julia else widget._FORMULA_CENTERS.get(widget._formula, (-0.5, 0.0))[1]
        widget._scale = 3.0
        self.render(widget)
        return widget._scale

    def set_power(self, widget: FractalViewportWidget, power: int) -> None:
        widget._power = power
        if widget._formula in ("multibrot", "newton"):
            self.render(widget)

    def set_phoenix_constant(self, widget: FractalViewportWidget, real: float, imag: float) -> None:
        widget._phoenix_real = real
        widget._phoenix_imag = imag
        if widget._formula == "phoenix":
            self.render(widget)

    def set_scale(self, widget: FractalViewportWidget, scale: float) -> None:
        widget._scale = max(1e-12, scale)
        self.render(widget)

    def set_julia_constant(self, widget: FractalViewportWidget, real: float, imag: float) -> None:
        widget._julia_real = real
        widget._julia_imag = imag
        if widget._is_julia:
            self.render(widget)

    def set_max_iterations(self, widget: FractalViewportWidget, value: int) -> None:
        widget._max_iterations = value
        self.render(widget)

    def set_coloring_mode(self, widget: FractalViewportWidget, mode: str) -> None:
        widget._coloring_mode = mode
        self.render(widget)

    def set_trap_point(self, widget: FractalViewportWidget, x: float, y: float) -> None:
        widget._trap_x = x
        widget._trap_y = y
        if widget._coloring_mode == "orbit_trap_point":
            self.render(widget)

    def set_palette_offset(self, widget: FractalViewportWidget, offset: float) -> None:
        widget._palette_offset = offset % 1.0
        self.render(widget)

    def set_cycle_active(self, widget: FractalViewportWidget, active: bool) -> None:
        widget._cycle_active = active
        if active:
            widget._cycle_timer.start()
        else:
            widget._cycle_timer.stop()

    def set_cycle_speed(self, widget: FractalViewportWidget, steps_per_second: float) -> None:
        interval = max(16, int(1000.0 / max(steps_per_second, 0.1)))
        widget._cycle_timer.setInterval(interval)

    def advance_cycle(self, widget: FractalViewportWidget) -> None:
        widget._palette_offset = (widget._palette_offset + 0.005) % 1.0
        self.render(widget)

    def handle_resize(self, widget: FractalViewportWidget) -> None:
        self.render(widget)

    def handle_wheel(self, widget: FractalViewportWidget, delta_y: float) -> float:
        factor = 0.85 if delta_y > 0 else 1.0 / 0.85
        widget._scale = max(1e-12, widget._scale * factor)
        self.render(widget)
        return widget._scale

    def handle_mouse_press(self, widget: FractalViewportWidget, x: float, y: float) -> None:
        widget._pan_origin = (x, y)
        widget._pan_center_start = (widget._center_x, widget._center_y)

    def handle_mouse_double_click(self, widget: FractalViewportWidget, x: float, y: float) -> None:
        widget._pan_origin = None
        aspect = widget.width() / max(1, widget.height())
        widget._center_x += (x / widget.width() - 0.5) * widget._scale * aspect
        widget._center_y += (0.5 - y / widget.height()) * widget._scale
        self.render(widget)

    def handle_mouse_move(self, widget: FractalViewportWidget, x: float, y: float) -> None:
        if widget._pan_origin is None:
            return
        dx = x - widget._pan_origin[0]
        dy = y - widget._pan_origin[1]
        aspect = widget.width() / max(1, widget.height())
        widget._center_x = widget._pan_center_start[0] - dx / widget.width() * widget._scale * aspect
        widget._center_y = widget._pan_center_start[1] + dy / widget.height() * widget._scale
        self.render(widget)

    def handle_mouse_release(self, widget: FractalViewportWidget) -> None:
        widget._pan_origin = None

    def render(self, widget: FractalViewportWidget) -> ViewportRenderResult:
        if not self._backend.available or not widget._palette:
            return ViewportRenderResult(image=None, status=None)

        width = max(1, widget.width())
        height = max(1, widget.height())
        state = widget.to_state()
        raw = self._backend.render_fractal(
            state.formula,
            width,
            height,
            is_julia=state.is_julia,
            julia_real=state.julia_real,
            julia_imag=state.julia_imag,
            power=state.power,
            phoenix_real=state.phoenix_real,
            phoenix_imag=state.phoenix_imag,
            center_x=state.center_x,
            center_y=state.center_y,
            scale=state.scale,
            max_iterations=state.max_iterations,
            palette=widget._palette,
            coloring_mode=state.coloring_mode,
            trap_x=state.trap_x,
            trap_y=state.trap_y,
            palette_offset=state.palette_offset,
        )
        image = QImage(raw, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()
        label = state.formula.replace("_", " ").title()
        mode = "Julia" if state.is_julia else "Mandelbrot"
        extra = f" (n={state.power})" if state.formula == "multibrot" else ""
        status = (
            f"{label}{extra} · {mode} | "
            f"center ({state.center_x:.4f}, {state.center_y:.4f}) | "
            f"scale {state.scale:.4g} | "
            f"{state.max_iterations} iters"
        )
        widget._image = image
        widget.update()
        widget.status_changed.emit(status)
        return ViewportRenderResult(image=image, status=status)
