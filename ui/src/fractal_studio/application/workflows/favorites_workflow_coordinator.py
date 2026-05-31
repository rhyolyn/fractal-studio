from __future__ import annotations

import datetime
from collections.abc import Callable

from fractal_studio.editor import ColorCubeEditor, PalettePreviewWidget
from fractal_studio.application.controllers.favorites_controller import (
    FavoritesController,
)
from fractal_studio.application.coordinators.favorites_panel_coordinator import (
    FavoritesPanelCoordinator,
)
from fractal_studio.state import FavoriteSnapshot, ViewportState
from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget


class FavoritesWorkflowCoordinator:
    def __init__(
        self,
        favorites_controller: FavoritesController,
        favorites_panel: FavoritesPanelCoordinator,
    ) -> None:
        self._favorites_controller = favorites_controller
        self._favorites_panel = favorites_panel

    def save_favorite(
        self,
        *,
        viewport: FractalViewportWidget | None,
        editor: ColorCubeEditor | None,
        aspect_ratio_mode: str,
        favorites: list[FavoriteSnapshot],
        build_name: Callable[[ViewportState], str],
        capture_thumbnail: Callable[[], str],
        add_favorite: Callable[[FavoriteSnapshot], None],
        add_row: Callable[[FavoriteSnapshot], None],
        persist_favorites: Callable[[], None],
        show_status: Callable[[str], None],
    ) -> None:
        if viewport is None:
            return
        viewport_state = viewport.to_state()
        palette = list(viewport.palette())
        control_points = list(editor.control_points) if editor is not None else []
        self._favorites_controller.save_favorite(
            viewport_state=viewport_state,
            palette=palette,
            control_points=control_points,
            aspect_ratio_mode=aspect_ratio_mode,
            favorites=favorites,
            build_name=build_name,
            capture_thumbnail=capture_thumbnail,
            add_favorite=add_favorite,
            add_row=add_row,
            persist=persist_favorites,
            show_status=show_status,
        )

    def build_favorite_name(
        self,
        *,
        state: ViewportState,
        favorites: list[FavoriteSnapshot],
        now: Callable[[], datetime.datetime],
    ) -> str:
        existing_names = {fav.name for fav in favorites}
        return self._favorites_controller.build_favorite_name(
            state, existing_names, now
        )

    def load_selected_favorite(
        self,
        *,
        viewport: FractalViewportWidget | None,
        params_panel: FractalParamsPanel | None,
        selected_row: object | None,
        load_row: Callable[[object], None],
    ) -> None:
        if viewport is None or params_panel is None or selected_row is None:
            return
        load_row(selected_row)

    def delete_selected_favorite(
        self,
        *,
        selected_row: object | None,
        rows: list[object],
        favorites: list[FavoriteSnapshot],
        scroll_layout,
        persist_favorites: Callable[[], None],
    ) -> object | None:
        selected_row = self._favorites_panel.delete_selected(
            selected_row=selected_row,
            rows=rows,
            favorites=favorites,
            scroll_layout=scroll_layout,
        )
        if selected_row is None:
            persist_favorites()
        return selected_row

    def load_favorite_row(
        self,
        *,
        row: object,
        favorites: list[FavoriteSnapshot],
        rows: list[object],
        viewport: FractalViewportWidget | None,
        params_panel: FractalParamsPanel | None,
        editor: ColorCubeEditor | None,
        preview_palette: PalettePreviewWidget | None,
        apply_aspect_ratio_mode: Callable[[str], None],
        select_row: Callable[[object], None],
        show_status: Callable[[str], None],
    ) -> None:
        def _do_restore(snapshot: FavoriteSnapshot) -> None:
            self._favorites_controller.restore_snapshot(
                snapshot=snapshot,
                apply_viewport_state=lambda state, rerender: (
                    viewport.apply_state(state, rerender=rerender) if viewport else None
                ),
                apply_control_points=lambda pts: (
                    editor.set_control_points(pts) if editor else None
                ),
                apply_palette=lambda pal: (
                    viewport.set_palette(pal) if viewport else None,
                    preview_palette.set_palette(pal) if preview_palette else None,
                ),
                apply_params=lambda params: (
                    params_panel.apply_state(params) if params_panel else None
                ),
                set_cycle_active=lambda active: (
                    viewport.set_cycle_active(active) if viewport else None
                ),
                apply_aspect_ratio_mode=apply_aspect_ratio_mode,
            )

        self._favorites_controller.load_favorite_row(
            row=row,
            favorites=favorites,
            rows=rows,
            restore_snapshot=_do_restore,
            select_row=select_row,
            show_status=show_status,
        )
