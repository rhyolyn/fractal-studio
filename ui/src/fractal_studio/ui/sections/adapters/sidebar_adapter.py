from __future__ import annotations

from fractal_studio.ui.sections.adapters.base import _BasePortsAdapter
from fractal_studio.viewport import FractalParamsPanel


class SidebarPanelPortsAdapter(_BasePortsAdapter):
    def set_params_panel(self, panel: FractalParamsPanel) -> None:
        self._state.sidebar.set_params_panel(panel)

    def connect_params_and_viewport(self) -> None:
        self._state.sidebar.connect_params_and_viewport()

    def backend_state_message(self) -> str:
        return self._state.sidebar.backend_state_message()
