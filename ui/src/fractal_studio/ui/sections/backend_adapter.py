from __future__ import annotations

from PySide6.QtWidgets import QLabel

from fractal_studio.ui.sections.base import _BasePortsAdapter


class BackendPanelPortsAdapter(_BasePortsAdapter):
    def set_backend_state_label(self, label: QLabel) -> None:
        self._state._sidebar_state.set_backend_state_label(label)
