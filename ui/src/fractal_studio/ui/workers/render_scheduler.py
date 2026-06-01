from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from fractal_studio.state import RenderRequest, ViewportState
from fractal_studio.ui.workers.render_worker import RenderResult

_DEBOUNCE_MS = 50


class RenderScheduler(QObject):
    render_requested = Signal(RenderRequest)
    render_ready = Signal(RenderResult)

    def __init__(self) -> None:
        super().__init__()
        self._generation: int = 0
        self._pending: RenderRequest | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(_DEBOUNCE_MS)
        self._timer.timeout.connect(self._fire)

    @property
    def current_generation(self) -> int:
        return self._generation

    def schedule(
        self,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
    ) -> None:
        self._generation += 1
        self._pending = RenderRequest(
            generation=self._generation,
            viewport_state=viewport_state,
            palette=list(palette),
            width=width,
            height=height,
        )
        self._timer.start()

    def _fire(self) -> None:
        if self._pending is not None:
            self.render_requested.emit(self._pending)
            self._pending = None

    @Slot(RenderResult)
    def _on_result(self, result: RenderResult) -> None:
        if result.generation == self._generation:
            self.render_ready.emit(result)
