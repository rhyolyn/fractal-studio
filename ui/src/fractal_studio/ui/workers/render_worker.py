from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage

from fractal_studio.state import RenderRequest, format_render_status

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
        raw = self._backend.render(request)
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
        self.render_complete.emit(RenderResult(
            generation=request.generation,
            image=image,
            status=format_render_status(request.viewport_state),
        ))
