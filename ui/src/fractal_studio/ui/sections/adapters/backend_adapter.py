from __future__ import annotations

from PySide6.QtWidgets import QLabel

from fractal_studio.ui.sections.adapters.base import _BasePortsAdapter


class BackendPanelPortsAdapter(_BasePortsAdapter):
    def set_backend_state_label(self, label: QLabel) -> None:
        self._state.sidebar.set_backend_state_label(label)
