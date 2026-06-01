from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Protocol

from PySide6.QtGui import QImage

from fractal_studio.backend import Color, CoreBackend
from fractal_studio.state import (
    JuliaParams,
    NewtonParams,
    PhoenixParams,
    ViewportState,
)

if TYPE_CHECKING:
    from fractal_studio.ui.workers.render_scheduler import RenderScheduler


class _ViewportAdapter(Protocol):
    status_changed: object

    def supported_aspect_ratio_modes(self) -> set[str]: ...
    def aspect_ratio_mode(self) -> str: ...
    def load_aspect_ratio_mode(self, mode: str) -> None: ...
    def heightForWidth(self, width: int) -> int: ...
    def setMinimumSize(self, width: int, height: int) -> None: ...
    def updateGeometry(self) -> None: ...
    def update(self) -> None: ...
    def replace_palette(self, palette: list[Color]) -> None: ...
    def palette(self) -> list[Color]: ...
    def to_state(self) -> ViewportState: ...
    def load_state(self, state: ViewportState) -> None: ...
    def formula_center(self, formula: str) -> tuple[float, float]: ...
    def newton_scale(self) -> float: ...
    def set_cycle_active_flag(self, active: bool) -> None: ...
    def start_cycle_timer(self) -> None: ...
    def stop_cycle_timer(self) -> None: ...
    def set_cycle_interval(self, interval: int) -> None: ...
    def set_pan_anchor(
        self, origin: tuple[float, float], center_start: tuple[float, float]
    ) -> None: ...
    def pan_origin(self) -> tuple[float, float] | None: ...
    def pan_center_start(self) -> tuple[float, float]: ...
    def clear_pan_anchor(self) -> None: ...
    def store_rendered_image(self, image: QImage) -> None: ...
    def width(self) -> int: ...
    def height(self) -> int: ...


@dataclass(frozen=True)
class ViewportRenderResult:
    image: QImage | None
    status: str | None


class ViewportController:
    def __init__(self, backend: CoreBackend, scheduler: RenderScheduler | None = None) -> None:
        self._backend = backend
        self._scheduler = scheduler

    def apply_aspect_ratio_mode(self, widget: _ViewportAdapter, mode: str) -> str:
        if mode not in widget.supported_aspect_ratio_modes():
            mode = "square"
        if mode == widget.aspect_ratio_mode():
            return mode

        widget.load_aspect_ratio_mode(mode)
        widget.setMinimumSize(320, widget.heightForWidth(320))
        widget.updateGeometry()
        widget.update()
        return mode

    def set_palette(self, widget: _ViewportAdapter, palette: list[Color]) -> None:
        widget.replace_palette(list(palette))
        self.render(widget)

    def apply_state(
        self, widget: _ViewportAdapter, state: ViewportState, *, rerender: bool = True
    ) -> None:
        widget.load_state(
            replace(
                state,
                scale=max(1e-12, state.scale),
                max_iterations=max(1, state.max_iterations),
                is_julia=bool(state.is_julia),
                power=max(2, state.power),
                palette_offset=state.palette_offset % 1.0,
            )
        )

        if rerender:
            self.render(widget)

    def set_formula(self, widget: _ViewportAdapter, formula: str) -> float:
        current = widget.to_state()
        is_julia = current.is_julia
        if formula == "newton":
            is_julia = False
        cx, cy = widget.formula_center(formula) if not is_julia else (0.0, 0.0)
        default_scale = widget.newton_scale() if formula == "newton" else 3.0
        widget.load_state(
            replace(
                current,
                formula=formula,
                is_julia=is_julia,
                center_x=cx,
                center_y=cy,
                scale=default_scale,
            )
        )
        self.render(widget)
        return default_scale

    def set_mode(self, widget: _ViewportAdapter, is_julia: bool) -> float:
        current = widget.to_state()
        cx, cy = (0.0, 0.0) if is_julia else widget.formula_center(current.formula)
        widget.load_state(
            replace(
                current,
                is_julia=is_julia,
                center_x=cx,
                center_y=cy,
                scale=3.0,
            )
        )
        self.render(widget)
        return 3.0

    def set_power(self, widget: _ViewportAdapter, power: int) -> None:
        current = widget.to_state()
        widget.load_state(replace(current, power=power))
        if current.formula in ("multibrot", "newton"):
            self.render(widget)

    def set_phoenix_constant(
        self, widget: _ViewportAdapter, real: float, imag: float
    ) -> None:
        current = widget.to_state()
        widget.load_state(
            replace(current, formula_params=PhoenixParams(real=real, imag=imag))
        )
        if current.formula == "phoenix":
            self.render(widget)

    def set_scale(self, widget: _ViewportAdapter, scale: float) -> None:
        current = widget.to_state()
        widget.load_state(replace(current, scale=max(1e-12, scale)))
        self.render(widget)

    def set_julia_constant(
        self, widget: _ViewportAdapter, real: float, imag: float
    ) -> None:
        current = widget.to_state()
        widget.load_state(
            replace(current, formula_params=JuliaParams(cx=real, cy=imag))
        )
        if current.is_julia:
            self.render(widget)

    def set_max_iterations(self, widget: _ViewportAdapter, value: int) -> None:
        current = widget.to_state()
        widget.load_state(replace(current, max_iterations=value))
        self.render(widget)

    def set_coloring_mode(self, widget: _ViewportAdapter, mode: str) -> None:
        current = widget.to_state()
        widget.load_state(replace(current, coloring_mode=mode))
        self.render(widget)

    def set_trap_point(self, widget: _ViewportAdapter, x: float, y: float) -> None:
        current = widget.to_state()
        widget.load_state(
            replace(current, formula_params=NewtonParams(trap_x=x, trap_y=y))
        )
        if current.coloring_mode == "orbit_trap_point":
            self.render(widget)

    def set_palette_offset(self, widget: _ViewportAdapter, offset: float) -> None:
        current = widget.to_state()
        widget.load_state(replace(current, palette_offset=offset % 1.0))
        self.render(widget)

    def set_cycle_active(self, widget: _ViewportAdapter, active: bool) -> None:
        widget.set_cycle_active_flag(active)
        if active:
            widget.start_cycle_timer()
        else:
            widget.stop_cycle_timer()

    def set_cycle_speed(
        self, widget: _ViewportAdapter, steps_per_second: float
    ) -> None:
        interval = max(16, int(1000.0 / max(steps_per_second, 0.1)))
        widget.set_cycle_interval(interval)

    def advance_cycle(self, widget: _ViewportAdapter) -> None:
        current = widget.to_state()
        widget.load_state(
            replace(current, palette_offset=(current.palette_offset + 0.005) % 1.0)
        )
        self.render(widget)

    def handle_resize(self, widget: _ViewportAdapter) -> bool:
        return True

    def handle_wheel(self, widget: _ViewportAdapter, delta_y: float) -> float:
        current = widget.to_state()
        factor = 0.85 if delta_y > 0 else 1.0 / 0.85
        scale = max(1e-12, current.scale * factor)
        widget.load_state(replace(current, scale=scale))
        self.render(widget)
        return scale

    def handle_mouse_press(self, widget: _ViewportAdapter, x: float, y: float) -> None:
        state = widget.to_state()
        widget.set_pan_anchor((x, y), (state.center_x, state.center_y))

    def handle_mouse_double_click(
        self, widget: _ViewportAdapter, x: float, y: float
    ) -> None:
        state = widget.to_state()
        widget.clear_pan_anchor()
        aspect = widget.width() / max(1, widget.height())
        widget.load_state(
            replace(
                state,
                center_x=state.center_x
                + (x / widget.width() - 0.5) * state.scale * aspect,
                center_y=state.center_y + (0.5 - y / widget.height()) * state.scale,
            )
        )
        self.render(widget)

    def handle_mouse_move(self, widget: _ViewportAdapter, x: float, y: float) -> bool:
        origin = widget.pan_origin()
        if origin is None:
            return False
        center_start = widget.pan_center_start()
        state = widget.to_state()
        dx = x - origin[0]
        dy = y - origin[1]
        aspect = widget.width() / max(1, widget.height())
        widget.load_state(
            replace(
                state,
                center_x=center_start[0] - dx / widget.width() * state.scale * aspect,
                center_y=center_start[1] + dy / widget.height() * state.scale,
            )
        )
        return True

    def handle_mouse_release(self, widget: _ViewportAdapter) -> None:
        widget.clear_pan_anchor()

    def render(self, widget: _ViewportAdapter) -> ViewportRenderResult:
        if self._scheduler is not None:
            palette = widget.palette()
            if self._backend.capabilities.can_render and palette:
                self._scheduler.schedule(
                    viewport_state=widget.to_state(),
                    palette=palette,
                    width=max(1, widget.width()),
                    height=max(1, widget.height()),
                )
            return ViewportRenderResult(image=None, status=None)

        # Fallback: synchronous render when no scheduler is wired (used in tests)
        palette = widget.palette()
        if not self._backend.capabilities.can_render or not palette:
            return ViewportRenderResult(image=None, status=None)

        width = max(1, widget.width())
        height = max(1, widget.height())
        state = widget.to_state()
        kwargs = state.to_render_kwargs()
        raw = self._backend.render_fractal(
            state.formula, width, height,
            is_julia=state.is_julia,
            julia_real=kwargs["julia_real"],
            julia_imag=kwargs["julia_imag"],
            power=state.power,
            phoenix_real=kwargs["phoenix_real"],
            phoenix_imag=kwargs["phoenix_imag"],
            center_x=state.center_x,
            center_y=state.center_y,
            scale=state.scale,
            max_iterations=state.max_iterations,
            palette=palette,
            coloring_mode=state.coloring_mode,
            trap_x=kwargs["trap_x"],
            trap_y=kwargs["trap_y"],
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
        widget.store_rendered_image(image)
        widget.update()
        widget.status_changed.emit(status)
        return ViewportRenderResult(image=image, status=status)
