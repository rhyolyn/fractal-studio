from __future__ import annotations

from collections.abc import Callable

from fractal_studio.backend import CoreBackend
from fractal_studio.state import RenderRequest, ViewportState


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
        request = RenderRequest(
            generation=0,
            viewport_state=viewport_state,
            palette=tuple(palette),
            width=width,
            height=height,
        )
        raw = self._backend.render(request)
        if not raw:
            set_status("Backend not available — no render produced.")
            return None
        return raw
