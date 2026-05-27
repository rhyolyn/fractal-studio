from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QComboBox, QLabel, QSpinBox, QVBoxLayout, QWidget

from fractal_studio.editor import ColorCubeEditor, PalettePreviewWidget
from fractal_studio.thumbnail_utils import encode_pixmap
from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget

if TYPE_CHECKING:
    from fractal_studio.backend import BackendProfile
    from fractal_studio.main_window import MainWindow


class MainWindowSectionsMediator:
    def __init__(self, owner: MainWindow) -> None:
        self._owner = owner

    @property
    def backend(self):
        return self._owner.backend

    @property
    def backend_profile(self) -> BackendProfile:
        return self._owner.backend_profile

    @property
    def backend_loaded(self) -> bool:
        return self._owner.backend_loaded

    @property
    def viewport(self) -> FractalViewportWidget | None:
        return self._owner.viewport

    @property
    def editor(self) -> ColorCubeEditor | None:
        return self._owner.editor

    @property
    def preview_palette(self) -> PalettePreviewWidget | None:
        return self._owner.preview_palette

    @property
    def preview_legacy(self) -> PalettePreviewWidget | None:
        return self._owner.preview_legacy

    @property
    def point_summary(self) -> QLabel | None:
        return self._owner.point_summary

    @property
    def palette_summary(self) -> QLabel | None:
        return self._owner.palette_summary

    @property
    def favorites(self) -> list[dict]:
        return self._owner._favorites

    @property
    def favorite_rows(self):
        return self._owner._fav_rows

    @property
    def selected_row(self):
        return self._owner._selected_row

    @property
    def aspect_ratio_mode(self) -> str:
        return self._owner._aspect_ratio_mode

    @property
    def export_presets(self) -> list[tuple[str, int, int]]:
        return self._owner._export_presets

    @property
    def export_combo(self) -> QComboBox | None:
        return self._owner._export_combo

    def show_status(self, message: str) -> None:
        self._owner.statusBar().showMessage(message)

    def set_aspect_ratio_combo(self, combo: QComboBox) -> None:
        self._owner._aspect_ratio_combo = combo

    def on_aspect_ratio_changed(self, index: int) -> None:
        self._owner._export_panel.on_aspect_ratio_changed(
            index=index,
            apply_aspect_ratio_mode=self._owner._apply_aspect_ratio_mode,
        )

    def set_viewport(self, viewport: FractalViewportWidget) -> None:
        self._owner.viewport = viewport

    def set_viewport_hint_label(self, label: QLabel) -> None:
        self._owner.viewport_hint_label = label

    def set_preview_widgets(self, preview_palette: PalettePreviewWidget, preview_legacy: PalettePreviewWidget) -> None:
        self._owner.preview_palette = preview_palette
        self._owner.preview_legacy = preview_legacy

    def set_palette_summary_labels(self, point_summary: QLabel, palette_summary: QLabel) -> None:
        self._owner.point_summary = point_summary
        self._owner.palette_summary = palette_summary

    def set_editor(self, editor: ColorCubeEditor) -> None:
        self._owner.editor = editor

    def update_palette_previews(self, palette) -> None:
        self._owner._palette_preview.update_palette_previews(
            palette=palette,
            editor=self._owner.editor,
            backend=self._owner.backend,
            legacy_palette_size=self._owner.backend_profile.legacy_palette_size,
            preview_palette=self._owner.preview_palette,
            preview_legacy=self._owner.preview_legacy,
            palette_summary=self._owner.palette_summary,
        )

    def update_control_summary(self, points) -> None:
        self._owner._palette_preview.update_control_summary(self._owner.point_summary, points)

    def save_favorite(self) -> None:
        self._owner._favorites_workflow.save_favorite(
            viewport=self._owner.viewport,
            editor=self._owner.editor,
            aspect_ratio_mode=self._owner._aspect_ratio_mode,
            favorites=self._owner._favorites,
            build_name=lambda state: self._owner._favorites_workflow.build_favorite_name(
                state=state,
                favorites=self._owner._favorites,
                now=datetime.datetime.now,
            ),
            capture_thumbnail=lambda: encode_pixmap(self._owner.viewport.grab()),
            add_favorite=self._owner._favorites.append,
            add_row=self._owner._add_favorite_row,
            persist_favorites=lambda: self._owner._favorites_controller.persist_favorites(
                self._owner._favorites,
                self._owner._favorites_repo.save,
            ),
            show_status=self.show_status,
        )

    def load_palette_json(self) -> None:
        self._owner._palette_panel.load_palette_json(
            parent=self._owner,
            editor=self._owner.editor,
            backend=self._owner.backend,
            set_status=self.show_status,
        )

    def export_legacy_map(self) -> None:
        self._owner._palette_panel.export_legacy_map(
            parent=self._owner,
            editor=self._owner.editor,
            backend=self._owner.backend,
            legacy_palette_size=self._owner.backend_profile.legacy_palette_size,
            set_status=self.show_status,
        )

    def set_backend_state_label(self, label: QLabel) -> None:
        self._owner.backend_state_label = label

    def refresh_export_presets(self, combo: QComboBox) -> None:
        self._owner._export_combo = combo
        self._owner._export_presets = self._owner._export_panel.refresh_export_presets(
            aspect_ratio_mode=self._owner._aspect_ratio_mode,
            export_combo=self._owner._export_combo,
            current_presets=self._owner._export_presets,
            on_export_preset_changed=self._owner._on_export_preset_changed,
        )

    def on_export_clicked(self) -> None:
        self._owner._export_panel.on_export_clicked(
            export_presets=self._owner._export_presets,
            export_combo=self._owner._export_combo,
            custom_width_box=self._owner._custom_width_box,
            custom_height_box=self._owner._custom_height_box,
            set_custom_size=lambda w, h: setattr(self._owner, "_custom_width", w)
            or setattr(self._owner, "_custom_height", h),
            export_callback=lambda width, height: self._owner._controller.export_render(
                self._owner,
                self._owner.viewport,
                width,
                height,
                self.show_status,
            ),
        )

    def set_custom_size_boxes(self, width_box: QSpinBox, height_box: QSpinBox) -> None:
        self._owner._custom_width_box = width_box
        self._owner._custom_height_box = height_box

    def custom_size_values(self) -> tuple[int, int]:
        return self._owner._custom_width, self._owner._custom_height

    def on_export_preset_changed(self, index: int) -> None:
        self._owner._on_export_preset_changed(index)

    def apply_aspect_ratio_mode(self, update_combo: bool) -> None:
        self._owner._apply_aspect_ratio_mode(self._owner._aspect_ratio_mode, update_combo=update_combo)

    def set_favorites_scroll_container(self, widget: QWidget, layout: QVBoxLayout) -> None:
        self._owner._fav_scroll_widget = widget
        self._owner._fav_scroll_layout = layout

    def load_favorites(self) -> list[dict]:
        self._owner._favorites = self._owner._favorites_controller.load_favorites(self._owner._favorites_repo.load)
        return self._owner._favorites

    def add_favorite_row(self, favorite: dict) -> None:
        self._owner._add_favorite_row(favorite)

    def delete_selected_favorite(self) -> None:
        self._owner._selected_row = self._owner._favorites_workflow.delete_selected_favorite(
            selected_row=self._owner._selected_row,
            rows=self._owner._fav_rows,
            favorites=self._owner._favorites,
            scroll_layout=self._owner._fav_scroll_layout,
            persist_favorites=lambda: self._owner._favorites_controller.persist_favorites(
                self._owner._favorites,
                self._owner._favorites_repo.save,
            ),
        )

    def set_params_panel(self, panel: FractalParamsPanel) -> None:
        self._owner.params_panel = panel

    def connect_params_and_viewport(self) -> None:
        self._owner._sidebar_wiring.connect_params_and_viewport(self._owner.params_panel, self._owner.viewport)

    def backend_state_message(self) -> str:
        return self._owner._settings_service.backend_state_message(
            self._owner.backend_loaded,
            self._owner.backend.available,
        )
