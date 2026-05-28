from __future__ import annotations

from PySide6.QtWidgets import QLabel

from fractal_studio.ui.sections.adapters.base import _BasePortsAdapter
from fractal_studio.editor import PalettePreviewWidget


class PalettePanelPortsAdapter(_BasePortsAdapter):
    def set_preview_widgets(
        self,
        preview_palette: PalettePreviewWidget,
        preview_legacy: PalettePreviewWidget,
    ) -> None:
        self._state._palette_state.set_preview_widgets(preview_palette, preview_legacy)

    def set_palette_summary_labels(
        self, point_summary: QLabel, palette_summary: QLabel
    ) -> None:
        self._state._palette_state.set_palette_summary_labels(
            point_summary, palette_summary
        )
