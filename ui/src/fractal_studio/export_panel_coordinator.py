from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QComboBox, QSpinBox

from fractal_studio.main_window_controller import MainWindowController
from fractal_studio.viewport import FractalViewportWidget


class ExportPanelCoordinator:
    def __init__(self, controller: MainWindowController) -> None:
        self._controller = controller

    def refresh_export_presets(
        self,
        *,
        aspect_ratio_mode: str,
        export_combo: QComboBox | None,
        current_presets: list[tuple[str, int, int]],
        on_export_preset_changed: Callable[[int], None],
    ) -> list[tuple[str, int, int]]:
        return self._controller.refresh_export_presets(
            aspect_ratio_mode=aspect_ratio_mode,
            export_combo=export_combo,
            current_presets=current_presets,
            on_export_preset_changed=on_export_preset_changed,
        )

    def apply_aspect_ratio_mode(
        self,
        *,
        mode: str,
        viewport: FractalViewportWidget | None,
        aspect_ratio_combo: QComboBox | None,
        refresh_export_presets: Callable[[], None],
        update_combo: bool = True,
    ) -> str:
        return self._controller.apply_aspect_ratio_mode(
            mode=mode,
            viewport=viewport,
            aspect_ratio_combo=aspect_ratio_combo,
            refresh_export_presets=refresh_export_presets,
            update_combo=update_combo,
        )

    def on_aspect_ratio_changed(
        self,
        *,
        index: int,
        apply_aspect_ratio_mode: Callable[[str, bool], None],
    ) -> None:
        mode = self._controller.aspect_mode_from_index(index)
        apply_aspect_ratio_mode(mode, False)

    def on_export_preset_changed(
        self,
        *,
        index: int,
        export_presets: list[tuple[str, int, int]],
        custom_width_box: QSpinBox | None,
        custom_height_box: QSpinBox | None,
        set_custom_row_visible: Callable[[bool], None],
    ) -> None:
        if custom_width_box is None or custom_height_box is None:
            return
        is_custom = self._controller.should_show_custom_size(index, len(export_presets))
        set_custom_row_visible(is_custom)

    def on_export_clicked(
        self,
        *,
        export_presets: list[tuple[str, int, int]],
        export_combo: QComboBox | None,
        custom_width_box: QSpinBox | None,
        custom_height_box: QSpinBox | None,
        set_custom_size: Callable[[int, int], None],
        export_callback: Callable[[int, int], None],
    ) -> None:
        if export_combo is None:
            return

        self._controller.on_export_clicked(
            export_presets=export_presets,
            index=export_combo.currentIndex(),
            custom_width_box=custom_width_box,
            custom_height_box=custom_height_box,
            set_custom_size=set_custom_size,
            export_callback=export_callback,
        )
