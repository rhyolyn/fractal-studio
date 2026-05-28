from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QFileDialog, QWidget

from fractal_studio.backend import CoreBackend
from fractal_studio.state import JuliaParams, NewtonParams, PhoenixParams
from fractal_studio.viewport import FractalViewportWidget


class ExportService:
    def __init__(self, backend: CoreBackend) -> None:
        self._backend = backend

    def export_render(
        self,
        parent: QWidget,
        viewport: FractalViewportWidget | None,
        width: int,
        height: int,
        set_status: Callable[[str], None],
    ) -> bool:
        if viewport is None or not self._backend.available:
            set_status("Backend not available.")
            return False

        path, _ = QFileDialog.getSaveFileName(
            parent,
            f"Export {width}x{height} render",
            str(Path.cwd() / f"fractal_{width}x{height}.png"),
            "PNG Image (*.png)",
        )
        if not path:
            return False

        set_status(f"Rendering {width}x{height}...")
        QApplication.processEvents()

        state = viewport.to_state()
        fp = state.formula_params
        julia_real = fp.cx if isinstance(fp, JuliaParams) else 0.0
        julia_imag = fp.cy if isinstance(fp, JuliaParams) else 0.0
        phoenix_real = fp.real if isinstance(fp, PhoenixParams) else 0.0
        phoenix_imag = fp.imag if isinstance(fp, PhoenixParams) else 0.0
        trap_x = fp.trap_x if isinstance(fp, NewtonParams) else 0.0
        trap_y = fp.trap_y if isinstance(fp, NewtonParams) else 0.0
        raw = self._backend.render_fractal(
            state.formula,
            width,
            height,
            is_julia=state.is_julia,
            julia_real=julia_real,
            julia_imag=julia_imag,
            power=state.power,
            phoenix_real=phoenix_real,
            phoenix_imag=phoenix_imag,
            center_x=state.center_x,
            center_y=state.center_y,
            scale=state.scale,
            max_iterations=state.max_iterations,
            palette=viewport.palette(),
            coloring_mode=state.coloring_mode,
            trap_x=trap_x,
            trap_y=trap_y,
            palette_offset=state.palette_offset,
        )

        image = QImage(
            raw, width, height, width * 4, QImage.Format.Format_RGBA8888
        ).copy()
        image.save(path)
        set_status(f"Saved {width}x{height} render to {path}")
        return True
