from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import QComboBox, QDialog, QSpinBox, QWidget

from fractal_studio.editor import ColorCubeEditor, PalettePreviewWidget
from fractal_studio.export_service import ExportService
from fractal_studio.favorites_controller import FavoritesController
from fractal_studio.state import FavoriteSnapshot, ViewportState
from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget


class MainWindowController:
    def __init__(self, export_service: ExportService, favorites_controller: FavoritesController) -> None:
        self._export_service = export_service
        self._favorites_controller = favorites_controller

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

    def build_export_presets_for_mode(self, aspect_mode: str) -> list[tuple[str, int, int]]:
        preset_sizes = {
            "square": [(1080, 1080), (1440, 1440), (2160, 2160)],
            "portrait": [(1080, 1440), (1440, 1920), (2160, 2880)],
            "landscape": [(1440, 1080), (1920, 1440), (2880, 2160)],
        }
        sizes = preset_sizes.get(aspect_mode, preset_sizes["square"])
        return [(f"{width} × {height}", width, height) for width, height in sizes] + [("Custom…", 0, 0)]

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
        previous_is_custom = bool(current_presets) and previous_index == len(current_presets) - 1
        new_presets = self.build_export_presets_for_mode(aspect_ratio_mode)

        export_combo.blockSignals(True)
        export_combo.clear()
        for label, _, _ in new_presets:
            export_combo.addItem(label)
        if previous_is_custom:
            export_combo.setCurrentIndex(len(new_presets) - 1)
        else:
            export_combo.setCurrentIndex(max(0, min(previous_index, len(new_presets) - 1)))
        export_combo.blockSignals(False)

        on_export_preset_changed(export_combo.currentIndex())
        return new_presets

    def open_settings_dialog(
        self,
        parent: QWidget,
        current_theme: str,
        dialog_factory: Callable[[str, QWidget], Any],
        apply_theme_name: Callable[[str, bool], None],
    ) -> None:
        original_theme = current_theme
        dialog = dialog_factory(current_theme, parent)
        dialog.theme_preview_requested.connect(lambda theme_name: apply_theme_name(theme_name, False))

        if dialog.exec() == QDialog.DialogCode.Accepted:
            apply_theme_name(dialog.selected_theme(), True)
        elif dialog.selected_theme() != original_theme:
            apply_theme_name(original_theme, False)

    def export_render(
        self,
        parent: QWidget,
        viewport: FractalViewportWidget | None,
        width: int,
        height: int,
        set_status: Callable[[str], None],
    ) -> bool:
        return self._export_service.export_render(parent, viewport, width, height, set_status)

    def build_favorite_snapshot(
        self,
        viewport: FractalViewportWidget,
        editor: ColorCubeEditor | None,
        aspect_ratio_mode: str,
        build_name: Callable[[ViewportState], str],
        capture_thumbnail: Callable[[], str],
    ) -> FavoriteSnapshot:
        state = viewport.to_state()
        control_points = editor.control_points if editor is not None else []
        return self._favorites_controller.build_snapshot(
            viewport=viewport,
            aspect_ratio_mode=aspect_ratio_mode,
            name=build_name(state),
            control_points=control_points,
            thumbnail=capture_thumbnail(),
        )

    def restore_favorite_snapshot(
        self,
        snapshot: FavoriteSnapshot,
        viewport: FractalViewportWidget,
        params_panel: FractalParamsPanel,
        editor: ColorCubeEditor | None,
        preview_palette: PalettePreviewWidget | None,
        apply_aspect_ratio_mode: Callable[[str], None],
    ) -> None:
        self._favorites_controller.restore_snapshot(
            snapshot=snapshot,
            viewport=viewport,
            params_panel=params_panel,
            editor=editor,
            preview_palette=preview_palette,
            apply_aspect_ratio_mode=apply_aspect_ratio_mode,
        )

    def sync_params_from_favorite(self, favorite: FavoriteSnapshot, params_panel: FractalParamsPanel) -> None:
        self._favorites_controller.sync_params_panel(favorite, params_panel)
