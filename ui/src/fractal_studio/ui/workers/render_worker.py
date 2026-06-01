from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage

from fractal_studio.state import RenderRequest

if TYPE_CHECKING:
    from fractal_studio.backend import CoreBackend


@dataclass(frozen=True)
class RenderResult:
    generation: int
    image: QImage | None
    status: str | None


class RenderWorker(QObject):
    render_complete = Signal(object)  # RenderResult — object type required for cross-thread queued delivery

    def __init__(self, backend: CoreBackend) -> None:
        super().__init__()
        self._backend = backend

    @Slot(object)  # RenderRequest — object type matches the Signal(object) on RenderScheduler
    def do_render(self, request: RenderRequest) -> None:
        state = request.viewport_state
        kwargs = state.to_render_kwargs()
        raw = self._backend.render_fractal(
            state.formula,
            request.width,
            request.height,
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
            palette=request.palette,
            coloring_mode=state.coloring_mode,
            trap_x=kwargs["trap_x"],
            trap_y=kwargs["trap_y"],
            palette_offset=state.palette_offset,
        )
        if not raw:
            self.render_complete.emit(RenderResult(
                generation=request.generation,
                image=None,
                status=None,
            ))
            return

        image = QImage(
            raw, request.width, request.height,
            request.width * 4, QImage.Format.Format_RGBA8888,
        ).copy()
        label = state.formula.replace("_", " ").title()
        mode = "Julia" if state.is_julia else "Mandelbrot"
        extra = f" (n={state.power})" if state.formula == "multibrot" else ""
        status = (
            f"{label}{extra} · {mode} | "
            f"center ({state.center_x:.4f}, {state.center_y:.4f}) | "
            f"scale {state.scale:.4g} | "
            f"{state.max_iterations} iters"
        )
        self.render_complete.emit(RenderResult(
            generation=request.generation,
            image=image,
            status=status,
        ))
