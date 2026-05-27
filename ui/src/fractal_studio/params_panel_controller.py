from __future__ import annotations


class ParamsPanelController:
    def handle_formula_changed(self, panel, index: int) -> str:
        formula = panel._FORMULAS[index][1]
        is_newton = formula == "newton"
        panel._set_power_visible(formula in ("multibrot", "newton"))
        panel._power_label.setText("Degree (n):" if is_newton else "Power (n):")
        panel._set_phoenix_visible(formula == "phoenix")
        panel._set_mode_visible(not is_newton)
        if is_newton:
            panel._mode_combo.setCurrentIndex(0)
        panel.formula_changed.emit(formula)
        return formula

    def handle_mode_changed(self, panel, text: str) -> bool:
        is_julia = text == "Julia"
        panel._set_julia_visible(is_julia)
        panel.mode_changed.emit(is_julia)
        return is_julia

    def handle_coloring_changed(self, panel, index: int):
        mode = panel._coloring_combo.itemData(index)
        panel._set_trap_point_visible(mode == "orbit_trap_point")
        panel.coloring_mode_changed.emit(mode)
        return mode

    def zoom_scale(self, default_scale: float, depth: float) -> float:
        return default_scale / (10.0 ** depth)

    def reset(self, panel) -> None:
        for combo in (panel._formula_combo, panel._mode_combo, panel._coloring_combo):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

        panel._power_spin.setValue(3)
        panel._phoenix_real_spin.setValue(0.5)
        panel._phoenix_imag_spin.setValue(0.0)
        panel._julia_real_spin.setValue(-0.8)
        panel._julia_imag_spin.setValue(0.156)
        panel._iterations_spin.setValue(256)
        panel._trap_x_spin.setValue(0.0)
        panel._trap_y_spin.setValue(0.0)
        if panel._cycle_button.isChecked():
            panel._cycle_button.setChecked(False)

        # Fire handlers explicitly so downstream listeners always observe reset state.
        self.handle_formula_changed(panel, 0)
        self.handle_mode_changed(panel, "Mandelbrot")
        self.handle_coloring_changed(panel, 0)
