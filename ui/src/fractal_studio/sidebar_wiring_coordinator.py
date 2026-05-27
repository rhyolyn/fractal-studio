from __future__ import annotations

from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget


class SidebarWiringCoordinator:
    def connect_params_and_viewport(
        self,
        params_panel: FractalParamsPanel,
        viewport: FractalViewportWidget | None,
    ) -> None:
        if viewport is None:
            return

        params_panel.formula_changed.connect(viewport.set_formula)
        params_panel.mode_changed.connect(viewport.set_mode)
        params_panel.power_changed.connect(viewport.set_power)
        params_panel.phoenix_changed.connect(viewport.set_phoenix_constant)
        params_panel.julia_constant_changed.connect(viewport.set_julia_constant)
        params_panel.max_iterations_changed.connect(viewport.set_max_iterations)
        params_panel.zoom_changed.connect(viewport.set_scale)
        viewport.scale_changed.connect(params_panel.set_scale)
        params_panel.coloring_mode_changed.connect(viewport.set_coloring_mode)
        params_panel.trap_point_changed.connect(viewport.set_trap_point)
        params_panel.cycle_toggled.connect(viewport.set_cycle_active)
        params_panel.cycle_speed_changed.connect(viewport.set_cycle_speed)
