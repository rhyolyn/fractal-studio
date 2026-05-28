from __future__ import annotations

from fractal_studio.ui.sections.base import _BasePortsAdapter
from fractal_studio.viewport import FractalParamsPanel


class SidebarPanelPortsAdapter(_BasePortsAdapter):
    def set_params_panel(self, panel: FractalParamsPanel) -> None:
        self._state._sidebar_state.set_params_panel(panel)

    def connect_params_and_viewport(self) -> None:
        self._state._sidebar_state.connect_params_and_viewport()

    def backend_state_message(self) -> str:
        return self._state._sidebar_state.backend_state_message()
