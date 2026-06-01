from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

from fractal_studio.state import ViewportState

if TYPE_CHECKING:
    from fractal_studio.services.export_service import ExportService


class ExportRunner(QObject):
    export_done = Signal(object)   # bytes | None
    status_changed = Signal(str)

    def __init__(
        self,
        export_service: ExportService,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
    ) -> None:
        super().__init__()
        self._service = export_service
        self._viewport_state = viewport_state
        self._palette = list(palette)
        self._width = width
        self._height = height

    @Slot()
    def run(self) -> None:
        raw = self._service.export_render(
            viewport_state=self._viewport_state,
            palette=self._palette,
            width=self._width,
            height=self._height,
            set_status=self._emit_status,
        )
        self.export_done.emit(raw)

    def _emit_status(self, message: str) -> None:
        self.status_changed.emit(message)
