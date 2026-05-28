from __future__ import annotations

from typing import Protocol


class _SignalLike(Protocol):
    def emit(self, *args) -> None: ...


class _ParamsPanelAdapter(Protocol):
    formula_changed: _SignalLike
    mode_changed: _SignalLike
    coloring_mode_changed: _SignalLike

    def formula_key(self, index: int) -> str: ...
    def set_power_visible(self, visible: bool) -> None: ...
    def set_power_label_text(self, text: str) -> None: ...
    def set_phoenix_visible(self, visible: bool) -> None: ...
    def set_mode_visible(self, visible: bool) -> None: ...
    def set_mode_index(self, index: int) -> None: ...
    def set_julia_visible(self, visible: bool) -> None: ...
    def coloring_mode(self, index: int): ...
    def set_trap_point_visible(self, visible: bool) -> None: ...
    def reset_controls(self) -> None: ...


class ParamsPanelController:
    def handle_formula_changed(self, panel: _ParamsPanelAdapter, index: int) -> str:
        formula = panel.formula_key(index)
        is_newton = formula == "newton"
        panel.set_power_visible(formula in ("multibrot", "newton"))
        panel.set_power_label_text("Degree (n):" if is_newton else "Power (n):")
        panel.set_phoenix_visible(formula == "phoenix")
        panel.set_mode_visible(not is_newton)
        if is_newton:
            panel.set_mode_index(0)
        panel.formula_changed.emit(formula)
        return formula

    def handle_mode_changed(self, panel: _ParamsPanelAdapter, text: str) -> bool:
        is_julia = text == "Julia"
        panel.set_julia_visible(is_julia)
        panel.mode_changed.emit(is_julia)
        return is_julia

    def handle_coloring_changed(self, panel: _ParamsPanelAdapter, index: int):
        mode = panel.coloring_mode(index)
        panel.set_trap_point_visible(mode == "orbit_trap_point")
        panel.coloring_mode_changed.emit(mode)
        return mode

    def zoom_scale(self, default_scale: float, depth: float) -> float:
        return default_scale / (10.0**depth)

    def reset(self, panel: _ParamsPanelAdapter) -> None:
        panel.reset_controls()

        # Fire handlers explicitly so downstream listeners always observe reset state.
        self.handle_formula_changed(panel, 0)
        self.handle_mode_changed(panel, "Mandelbrot")
        self.handle_coloring_changed(panel, 0)
