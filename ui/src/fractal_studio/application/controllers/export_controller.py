from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QComboBox, QSpinBox, QWidget

from fractal_studio.services.export_service import ExportService
from fractal_studio.viewport import FractalViewportWidget


class ExportController:
    """Controller for export and aspect ratio logic.

    Owns preset math, aspect ratio application, and export execution.
    """

    def __init__(self, export_service: ExportService) -> None:
        self._export_service = export_service

    def on_export_clicked(
        self,
        export_presets: list[tuple[str, int, int]],
        index: int,
        custom_width_box: QSpinBox | None,
        custom_height_box: QSpinBox | None,
        set_custom_size: Callable[[int, int], None],
        export_callback: Callable[[int, int], None],
    ) -> None:
        if index < 0 or index >= len(export_presets):
            return

        _, width, height = export_presets[index]
        if width == 0:
            if custom_width_box is None or custom_height_box is None:
                return
            width = custom_width_box.value()
            height = custom_height_box.value()
            set_custom_size(width, height)

        export_callback(width, height)

    def build_export_presets_for_mode(
        self, aspect_mode: str
    ) -> list[tuple[str, int, int]]:
        preset_sizes = {
            "square": [(1080, 1080), (1440, 1440), (2160, 2160)],
            "portrait": [(1080, 1440), (1440, 1920), (2160, 2880)],
            "landscape": [(1440, 1080), (1920, 1440), (2880, 2160)],
        }
        sizes = preset_sizes.get(aspect_mode, preset_sizes["square"])
        return [(f"{width} × {height}", width, height) for width, height in sizes] + [
            ("Custom…", 0, 0)
        ]

    def apply_aspect_ratio_mode(
        self,
        mode: str,
        viewport: FractalViewportWidget | None,
        aspect_ratio_combo: QComboBox | None,
        refresh_export_presets: Callable[[], None],
        update_combo: bool = True,
    ) -> str:
        if mode not in ("square", "portrait", "landscape"):
            mode = "square"

        if viewport is not None:
            viewport.set_aspect_ratio_mode(mode)

        if update_combo and aspect_ratio_combo is not None:
            index = {"square": 0, "portrait": 1, "landscape": 2}[mode]
            aspect_ratio_combo.blockSignals(True)
            aspect_ratio_combo.setCurrentIndex(index)
            aspect_ratio_combo.blockSignals(False)

        refresh_export_presets()
        return mode

    def aspect_mode_from_index(self, index: int) -> str:
        return {0: "square", 1: "portrait", 2: "landscape"}.get(index, "square")

    def should_show_custom_size(self, index: int, presets_count: int) -> bool:
        return index == presets_count - 1

    def refresh_export_presets(
        self,
        aspect_ratio_mode: str,
        export_combo: QComboBox | None,
        current_presets: list[tuple[str, int, int]],
        on_export_preset_changed: Callable[[int], None],
    ) -> list[tuple[str, int, int]]:
        if export_combo is None:
            return current_presets

        previous_index = export_combo.currentIndex()
        previous_is_custom = (
            bool(current_presets) and previous_index == len(current_presets) - 1
        )
        new_presets = self.build_export_presets_for_mode(aspect_ratio_mode)

        export_combo.blockSignals(True)
        export_combo.clear()
        for label, _, _ in new_presets:
            export_combo.addItem(label)
        if previous_is_custom:
            export_combo.setCurrentIndex(len(new_presets) - 1)
        else:
            export_combo.setCurrentIndex(
                max(0, min(previous_index, len(new_presets) - 1))
            )
        export_combo.blockSignals(False)

        on_export_preset_changed(export_combo.currentIndex())
        return new_presets

    def export_render(
        self,
        parent: QWidget,
        viewport: FractalViewportWidget | None,
        width: int,
        height: int,
        set_status: Callable[[str], None],
    ) -> bool:
        return self._export_service.export_render(
            parent, viewport, width, height, set_status
        )

