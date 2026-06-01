from __future__ import annotations

import datetime
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QComboBox, QFileDialog, QLabel, QSpinBox, QVBoxLayout, QWidget

from fractal_studio.editor import ColorCubeEditor, PalettePreviewWidget
from fractal_studio.state import FavoriteSnapshot
from fractal_studio.thumbnail_utils import (
    decode_thumbnail,
    encode_pixmap,
    placeholder_pixmap,
)
from fractal_studio.ui.widgets.favorite_thumbnail_row import FavoriteThumbnailRow
from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget

if TYPE_CHECKING:
    from fractal_studio.backend import CoreBackend
    from fractal_studio.application.workflows.favorites_workflow_coordinator import (
        FavoritesWorkflowCoordinator,
    )
    from fractal_studio.application.coordinators.export_panel_coordinator import (
        ExportPanelCoordinator,
    )
    from fractal_studio.application.controllers.favorites_controller import (
        FavoritesController,
    )
    from fractal_studio.application.coordinators.favorites_panel_coordinator import (
        FavoritesPanelCoordinator,
    )
    from fractal_studio.application.controllers.export_controller import (
        ExportController,
    )
    from fractal_studio.application.coordinators.palette_panel_coordinator import (
        PalettePanelCoordinator,
    )
    from fractal_studio.application.coordinators.palette_preview_coordinator import (
        PalettePreviewCoordinator,
    )
    from fractal_studio.persistence import FavoritesRepository
    from fractal_studio.services.settings_service import SettingsWorkflowService
    from fractal_studio.application.coordinators.sidebar_wiring_coordinator import (
        SidebarWiringCoordinator,
    )


class MainWindowViewportState:
    def __init__(
        self,
        *,
        controller: ExportController | None = None,
        export_panel: ExportPanelCoordinator | None = None,
        refresh_export_presets: Callable[[], None] | None = None,
    ) -> None:
        self._controller: ExportController | None = controller
        self._export_panel: ExportPanelCoordinator | None = export_panel
        self._refresh_export_presets: Callable[[], None] | None = refresh_export_presets
        self.viewport: FractalViewportWidget | None = None
        self.viewport_hint_label: QLabel | None = None
        self.aspect_ratio_combo: QComboBox | None = None
        self.aspect_ratio_mode: str = "square"

    def set_aspect_ratio_combo(self, combo: QComboBox) -> None:
        self.aspect_ratio_combo = combo

    def set_viewport(self, viewport: FractalViewportWidget) -> None:
        self.viewport = viewport

    def _on_render_ready(self, result: object) -> None:
        from fractal_studio.ui.workers.render_worker import RenderResult
        if not isinstance(result, RenderResult):
            return
        viewport = self.viewport
        if viewport is None or result.image is None:
            return
        viewport.store_rendered_image(result.image)
        viewport.update()
        if result.status:
            viewport.status_changed.emit(result.status)

    def set_viewport_hint_label(self, label: QLabel) -> None:
        self.viewport_hint_label = label

    def handle_aspect_ratio_changed(self, index: int) -> None:
        if self._export_panel is None:
            return
        self._export_panel.on_aspect_ratio_changed(
            index=index,
            apply_aspect_ratio_mode=self.apply_aspect_ratio_mode,
        )

    def apply_aspect_ratio_mode(self, mode: str, update_combo: bool = True) -> str:
        if self._controller is None or self._refresh_export_presets is None:
            return self.aspect_ratio_mode
        self.aspect_ratio_mode = mode
        self.aspect_ratio_mode = self._controller.apply_aspect_ratio_mode(
            mode=mode,
            viewport=self.viewport,
            aspect_ratio_combo=self.aspect_ratio_combo,
            refresh_export_presets=self._refresh_export_presets,
            update_combo=update_combo,
        )
        return self.aspect_ratio_mode


class MainWindowSidebarState:
    def __init__(
        self,
        *,
        sidebar_wiring: SidebarWiringCoordinator | None = None,
        viewport_getter: Callable[[], FractalViewportWidget | None] | None = None,
        settings_service: SettingsWorkflowService | None = None,
        backend_loaded_getter: Callable[[], bool] | None = None,
        backend_available_getter: Callable[[], bool] | None = None,
    ) -> None:
        self._sidebar_wiring: SidebarWiringCoordinator | None = sidebar_wiring
        self._viewport_getter: Callable[[], FractalViewportWidget | None] | None = (
            viewport_getter
        )
        self._settings_service: SettingsWorkflowService | None = settings_service
        self._backend_loaded_getter: Callable[[], bool] | None = backend_loaded_getter
        self._backend_available_getter: Callable[[], bool] | None = (
            backend_available_getter
        )
        self.params_panel: FractalParamsPanel | None = None
        self.backend_state_label: QLabel | None = None

    def set_backend_state_label(self, label: QLabel) -> None:
        self.backend_state_label = label

    def set_params_panel(self, panel: FractalParamsPanel) -> None:
        self.params_panel = panel

    def connect_params_and_viewport(self) -> None:
        if self._sidebar_wiring is None or self._viewport_getter is None:
            return
        self._sidebar_wiring.connect_params_and_viewport(
            self.params_panel, self._viewport_getter()
        )

    def backend_state_message(self) -> str:
        if (
            self._settings_service is None
            or self._backend_loaded_getter is None
            or self._backend_available_getter is None
        ):
            return ""
        return self._settings_service.backend_state_message(
            self._backend_loaded_getter(),
            self._backend_available_getter(),
        )


class MainWindowPaletteState:
    def __init__(
        self,
        *,
        palette_preview: PalettePreviewCoordinator | None = None,
        backend: CoreBackend | None = None,
        legacy_palette_size_getter: Callable[[], int | None] | None = None,
        editor_getter: Callable[[], ColorCubeEditor | None] | None = None,
    ) -> None:
        self._palette_preview: PalettePreviewCoordinator | None = palette_preview
        self._backend: CoreBackend | None = backend
        self._legacy_palette_size_getter: Callable[[], int | None] | None = (
            legacy_palette_size_getter
        )
        self._editor_getter: Callable[[], ColorCubeEditor | None] | None = editor_getter
        self.preview_palette: PalettePreviewWidget | None = None
        self.preview_legacy: PalettePreviewWidget | None = None
        self.point_summary: QLabel | None = None
        self.palette_summary: QLabel | None = None

    def set_preview_widgets(
        self,
        preview_palette: PalettePreviewWidget,
        preview_legacy: PalettePreviewWidget,
    ) -> None:
        self.preview_palette = preview_palette
        self.preview_legacy = preview_legacy

    def set_palette_summary_labels(
        self, point_summary: QLabel, palette_summary: QLabel
    ) -> None:
        self.point_summary = point_summary
        self.palette_summary = palette_summary

    def update_palette_previews(self, palette) -> None:
        if (
            self._palette_preview is None
            or self._backend is None
            or self._legacy_palette_size_getter is None
            or self._editor_getter is None
        ):
            return
        legacy_palette_size = self._legacy_palette_size_getter()
        if legacy_palette_size is None:
            return
        self._palette_preview.update_palette_previews(
            palette=palette,
            editor=self._editor_getter(),
            backend=self._backend,
            legacy_palette_size=legacy_palette_size,
            preview_palette=self.preview_palette,
            preview_legacy=self.preview_legacy,
            palette_summary=self.palette_summary,
        )

    def update_control_summary(self, points) -> None:
        if self._palette_preview is None:
            return
        self._palette_preview.update_control_summary(self.point_summary, points)


class MainWindowColormapState:
    def __init__(
        self,
        *,
        palette_panel: PalettePanelCoordinator | None = None,
        backend: CoreBackend | None = None,
        on_status: Callable[[str], None] | None = None,
        legacy_palette_size_getter: Callable[[], int | None] | None = None,
    ) -> None:
        self._palette_panel: PalettePanelCoordinator | None = palette_panel
        self._backend: CoreBackend | None = backend
        self._on_status: Callable[[str], None] | None = on_status
        self._legacy_palette_size_getter: Callable[[], int | None] | None = (
            legacy_palette_size_getter
        )
        self.editor: ColorCubeEditor | None = None

    def set_editor(self, editor: ColorCubeEditor) -> None:
        self.editor = editor

    def load_palette_json(self) -> None:
        if self._palette_panel is None or self._backend is None:
            return
        path_str, _ = QFileDialog.getOpenFileName(
            None,
            "Load palette",
            str(Path.cwd()),
            "Fractal Studio Palette (*.json)",
        )
        path = Path(path_str) if path_str else None
        self._palette_panel.load_palette_json(
            path=path,
            editor=self.editor,
            backend=self._backend,
            set_status=self._on_status if self._on_status is not None else lambda _: None,
        )

    def export_legacy_map(self) -> None:
        if (
            self._palette_panel is None
            or self._backend is None
            or self._legacy_palette_size_getter is None
        ):
            return
        legacy_palette_size = self._legacy_palette_size_getter()
        if legacy_palette_size is None:
            return
        path_str, _ = QFileDialog.getSaveFileName(
            None,
            "Export legacy palette",
            str(Path.cwd() / "palette.map"),
            "Legacy Palette (*.map)",
        )
        path = Path(path_str) if path_str else None
        self._palette_panel.export_legacy_map(
            path=path,
            editor=self.editor,
            backend=self._backend,
            legacy_palette_size=legacy_palette_size,
            set_status=self._on_status if self._on_status is not None else lambda _: None,
        )


class MainWindowFavoritesState:
    def __init__(
        self,
        *,
        favorites_controller: FavoritesController | None = None,
        favorites_panel: FavoritesPanelCoordinator | None = None,
        favorites_workflow: FavoritesWorkflowCoordinator | None = None,
        favorites_repo: FavoritesRepository | None = None,
        on_status: Callable[[str], None] | None = None,
        hover_panel_getter: Callable[[], QLabel | None] | None = None,
        viewport_getter: Callable[[], FractalViewportWidget | None] | None = None,
        params_panel_getter: Callable[[], FractalParamsPanel | None] | None = None,
        editor_getter: Callable[[], ColorCubeEditor | None] | None = None,
        preview_palette_getter: (
            Callable[[], PalettePreviewWidget | None] | None
        ) = None,
        apply_aspect_ratio_mode: Callable[[str, bool], str] | None = None,
        aspect_ratio_mode_getter: Callable[[], str] | None = None,
    ) -> None:
        self._favorites_controller: FavoritesController | None = favorites_controller
        self._favorites_panel: FavoritesPanelCoordinator | None = favorites_panel
        self._favorites_workflow: FavoritesWorkflowCoordinator | None = (
            favorites_workflow
        )
        self._favorites_repo: FavoritesRepository | None = favorites_repo
        self._on_status: Callable[[str], None] | None = on_status
        self._hover_panel_getter: Callable[[], QLabel | None] | None = (
            hover_panel_getter
        )
        self._viewport_getter: Callable[[], FractalViewportWidget | None] | None = (
            viewport_getter
        )
        self._params_panel_getter: Callable[[], FractalParamsPanel | None] | None = (
            params_panel_getter
        )
        self._editor_getter: Callable[[], ColorCubeEditor | None] | None = editor_getter
        self._preview_palette_getter: (
            Callable[[], PalettePreviewWidget | None] | None
        ) = preview_palette_getter
        self._apply_aspect_ratio_mode: Callable[[str, bool], str] | None = (
            apply_aspect_ratio_mode
        )
        self._aspect_ratio_mode_getter: Callable[[], str] | None = (
            aspect_ratio_mode_getter
        )
        self.favorites: list[FavoriteSnapshot] = []
        self.selected_row: FavoriteThumbnailRow | None = None
        self.fav_rows: list[FavoriteThumbnailRow] = []
        self.fav_scroll_widget: QWidget | None = None
        self.fav_scroll_layout: QVBoxLayout | None = None

    def set_favorites_scroll_container(
        self, widget: QWidget, layout: QVBoxLayout
    ) -> None:
        self.fav_scroll_widget = widget
        self.fav_scroll_layout = layout

    def load_favorites(self) -> list[FavoriteSnapshot]:
        if self._favorites_controller is None or self._favorites_repo is None:
            return []
        self.favorites = self._favorites_controller.load_favorites(
            self._favorites_repo.load
        )
        return self.favorites

    def add_favorite_row(self, favorite: FavoriteSnapshot) -> None:
        hover_panel = (
            None if self._hover_panel_getter is None else self._hover_panel_getter()
        )
        if (
            self._favorites_panel is None
            or self.fav_scroll_layout is None
            or hover_panel is None
        ):
            return
        row = self._favorites_panel.build_row_with_callbacks(
            favorite=favorite.to_dict(),
            owner=self,
            hover_panel=hover_panel,
            on_select_row=lambda mw, row: self.select_favorite_row(row),
            on_activate_row=lambda mw, row: self.activate_favorite_row(row),
            row_factory=FavoriteThumbnailRow,
            decode_thumbnail=decode_thumbnail,
            placeholder_pixmap=placeholder_pixmap,
        )
        self._favorites_panel.append_row(row, self.fav_rows, self.fav_scroll_layout)

    def delete_selected_favorite(self) -> None:
        if (
            self._favorites_workflow is None
            or self._favorites_controller is None
            or self._favorites_repo is None
        ):
            return
        self.selected_row = self._favorites_workflow.delete_selected_favorite(
            selected_row=self.selected_row,
            rows=self.fav_rows,
            favorites=self.favorites,
            scroll_layout=self.fav_scroll_layout,
            persist_favorites=lambda: self._favorites_controller.persist_favorites(
                self.favorites,
                self._favorites_repo.save,
            ),
        )

    def save_favorite(self) -> None:
        if (
            self._favorites_workflow is None
            or self._favorites_controller is None
            or self._favorites_repo is None
            or self._viewport_getter is None
            or self._editor_getter is None
            or self._aspect_ratio_mode_getter is None
        ):
            return
        viewport = self._viewport_getter()
        if viewport is None:
            return
        self._favorites_workflow.save_favorite(
            viewport=viewport,
            editor=self._editor_getter(),
            aspect_ratio_mode=self._aspect_ratio_mode_getter(),
            favorites=self.favorites,
            build_name=lambda viewport_state: (
                self._favorites_workflow.build_favorite_name(
                    state=viewport_state,
                    favorites=self.favorites,
                    now=datetime.datetime.now,
                )
            ),
            capture_thumbnail=lambda: encode_pixmap(viewport.grab()),
            add_favorite=self.favorites.append,
            add_row=self.add_favorite_row,
            persist_favorites=lambda: self._favorites_controller.persist_favorites(
                self.favorites,
                self._favorites_repo.save,
            ),
            show_status=self._on_status if self._on_status is not None else lambda _: None,
        )

    def select_favorite_row(self, row: FavoriteThumbnailRow) -> None:
        if self._favorites_panel is None:
            return
        self.selected_row = self._favorites_panel.select_row(self.selected_row, row)

    def activate_favorite_row(self, row: FavoriteThumbnailRow) -> None:
        if (
            self._favorites_workflow is None
            or self._viewport_getter is None
            or self._params_panel_getter is None
            or self._editor_getter is None
            or self._preview_palette_getter is None
            or self._apply_aspect_ratio_mode is None
        ):
            return
        self._favorites_workflow.load_favorite_row(
            row=row,
            favorites=self.favorites,
            rows=self.fav_rows,
            viewport=self._viewport_getter(),
            params_panel=self._params_panel_getter(),
            editor=self._editor_getter(),
            preview_palette=self._preview_palette_getter(),
            apply_aspect_ratio_mode=self._apply_aspect_ratio_mode,
            select_row=self.select_favorite_row,
            show_status=self._on_status if self._on_status is not None else lambda _: None,
        )


class MainWindowExportState:
    def __init__(
        self,
        *,
        export_panel: ExportPanelCoordinator | None = None,
        controller: ExportController | None = None,
        on_status: Callable[[str], None] | None = None,
        viewport_getter: Callable[[], FractalViewportWidget | None] | None = None,
        aspect_ratio_mode_getter: Callable[[], str] | None = None,
    ) -> None:
        self._export_panel: ExportPanelCoordinator | None = export_panel
        self._controller: ExportController | None = controller
        self._on_status: Callable[[str], None] | None = on_status
        self._viewport_getter: Callable[[], FractalViewportWidget | None] | None = (
            viewport_getter
        )
        self._aspect_ratio_mode_getter: Callable[[], str] | None = (
            aspect_ratio_mode_getter
        )
        self.export_combo: QComboBox | None = None
        self.export_presets: list[tuple[str, int, int]] = []
        self.custom_width: int = 1080
        self.custom_height: int = 1080
        self.custom_width_box: QSpinBox | None = None
        self.custom_height_box: QSpinBox | None = None

    def set_viewport_getter(self, getter: Callable[[], FractalViewportWidget | None]) -> None:
        self._viewport_getter = getter

    def set_aspect_ratio_mode_getter(self, getter: Callable[[], str]) -> None:
        self._aspect_ratio_mode_getter = getter

    def refresh_export_presets(self) -> None:
        if self._export_panel is None or self._aspect_ratio_mode_getter is None:
            return
        self.export_presets = self._export_panel.refresh_export_presets(
            aspect_ratio_mode=self._aspect_ratio_mode_getter(),
            export_combo=self.export_combo,
            current_presets=self.export_presets,
            on_export_preset_changed=self.on_export_preset_changed,
        )

    def set_custom_size_boxes(self, width_box: QSpinBox, height_box: QSpinBox) -> None:
        self.custom_width_box = width_box
        self.custom_height_box = height_box

    def custom_size_values(self) -> tuple[int, int]:
        return self.custom_width, self.custom_height

    def on_export_preset_changed(self, index: int) -> None:
        if self._export_panel is None:
            return
        self._export_panel.on_export_preset_changed(
            index=index,
            export_presets=self.export_presets,
            custom_width_box=self.custom_width_box,
            custom_height_box=self.custom_height_box,
            set_custom_row_visible=self.set_custom_export_row_visible,
        )

    def set_custom_export_row_visible(self, visible: bool) -> None:
        if self.custom_width_box is None:
            return
        custom_row = self.custom_width_box.parentWidget()
        if custom_row is not None:
            custom_row.setVisible(visible)

    def set_export_combo(self, combo: QComboBox) -> None:
        self.export_combo = combo

    def on_export_clicked(self) -> None:
        if (
            self._export_panel is None
            or self._controller is None
            or self._viewport_getter is None
        ):
            return
        viewport = self._viewport_getter()
        viewport_state = viewport.to_state() if viewport is not None else None
        palette = list(viewport.palette()) if viewport is not None else []
        on_status = self._on_status if self._on_status is not None else lambda _: None
        self._export_panel.on_export_clicked(
            export_presets=self.export_presets,
            export_combo=self.export_combo,
            custom_width_box=self.custom_width_box,
            custom_height_box=self.custom_height_box,
            set_custom_size=lambda width, height: (
                setattr(self, "custom_width", width)
                or setattr(self, "custom_height", height)
            ),
            export_callback=lambda width, height: self._do_export(
                viewport_state, palette, width, height, on_status
            ),
        )

    def _do_export(
        self,
        viewport_state: object,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
        on_status: Callable[[str], None],
    ) -> None:
        if self._controller is None:
            return

        path_str, _ = QFileDialog.getSaveFileName(
            None,
            f"Export {width}×{height} render",
            str(Path.cwd() / f"fractal_{width}x{height}.png"),
            "PNG Image (*.png)",
        )
        if not path_str:
            return

        raw = self._controller.export_render(viewport_state, palette, width, height, on_status)
        if raw is None:
            return

        image = QImage(raw, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()
        image.save(path_str)
        on_status(f"Saved {width}×{height} render to {path_str}")
