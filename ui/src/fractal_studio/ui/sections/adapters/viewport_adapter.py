from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel

from fractal_studio.ui.sections.adapters.base import _BasePortsAdapter
from fractal_studio.viewport import FractalViewportWidget


class ViewportPanelPortsAdapter(_BasePortsAdapter):
    def set_aspect_ratio_combo(self, combo: QComboBox) -> None:
        self._state.viewport.set_aspect_ratio_combo(combo)

    def on_aspect_ratio_changed(self, index: int) -> None:
        self._state.viewport.handle_aspect_ratio_changed(index)

    def set_viewport(self, viewport: FractalViewportWidget) -> None:
        self._state.viewport.set_viewport(viewport)

    def set_viewport_hint_label(self, label: QLabel) -> None:
        self._state.viewport.set_viewport_hint_label(label)
