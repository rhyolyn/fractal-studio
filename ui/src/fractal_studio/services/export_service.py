from __future__ import annotations

from collections.abc import Callable

from fractal_studio.backend import CoreBackend
from fractal_studio.state import ViewportState


class ExportService:
    def __init__(self, backend: CoreBackend) -> None:
        self._backend = backend

    def export_render(
        self,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
        set_status: Callable[[str], None],
    ) -> bytes | None:
        set_status(f"Rendering {width}×{height}...")
        kwargs = viewport_state.to_render_kwargs()
        raw = self._backend.render_fractal(
            viewport_state.formula,
            width,
            height,
            is_julia=viewport_state.is_julia,
            julia_real=kwargs["julia_real"],
            julia_imag=kwargs["julia_imag"],
            power=viewport_state.power,
            phoenix_real=kwargs["phoenix_real"],
            phoenix_imag=kwargs["phoenix_imag"],
            center_x=viewport_state.center_x,
            center_y=viewport_state.center_y,
            scale=viewport_state.scale,
            max_iterations=viewport_state.max_iterations,
            palette=palette,
            coloring_mode=viewport_state.coloring_mode,
            trap_x=kwargs["trap_x"],
            trap_y=kwargs["trap_y"],
            palette_offset=viewport_state.palette_offset,
        )
        if not raw:
            set_status("Backend not available — no render produced.")
            return None
        return raw
