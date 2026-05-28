from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QSpinBox

from fractal_studio.ui.sections.adapters.base import _BasePortsAdapter


class ExportPanelPortsAdapter(_BasePortsAdapter):
    def refresh_export_presets(self, combo: QComboBox) -> None:
        self._state._export_state.set_export_combo(combo)
        self._state._export_state.refresh_export_presets()

    def on_export_clicked(self) -> None:
        self._state._export_state.on_export_clicked()

    def set_custom_size_boxes(self, width_box: QSpinBox, height_box: QSpinBox) -> None:
        self._state._export_state.set_custom_size_boxes(width_box, height_box)

    def custom_size_values(self) -> tuple[int, int]:
        return self._state._export_state.custom_size_values()

    def on_export_preset_changed(self, index: int) -> None:
        self._state._export_state.on_export_preset_changed(index)

    def apply_aspect_ratio_mode(self, update_combo: bool) -> None:
        self._state._viewport_state.apply_aspect_ratio_mode(
            self._state._viewport_state.aspect_ratio_mode, update_combo=update_combo
        )
