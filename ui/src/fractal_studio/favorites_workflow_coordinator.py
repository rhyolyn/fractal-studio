from __future__ import annotations

import datetime
from collections.abc import Callable
from typing import Any

from fractal_studio.editor import ColorCubeEditor, PalettePreviewWidget
from fractal_studio.favorites_controller import FavoritesController
from fractal_studio.favorites_panel_coordinator import FavoritesPanelCoordinator
from fractal_studio.state import ViewportState
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
        favorites: list[dict],
        build_name: Callable[[ViewportState], str],
        capture_thumbnail: Callable[[], str],
        add_favorite: Callable[[dict], None],
        add_row: Callable[[dict], None],
        persist_favorites: Callable[[], None],
        show_status: Callable[[str], None],
    ) -> None:
        if viewport is None:
            return
        self._favorites_controller.save_favorite(
            viewport=viewport,
            editor=editor,
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
        favorites: list[dict],
        now: Callable[[], datetime.datetime],
    ) -> str:
        existing_names = {fav.get("name", "") for fav in favorites}
        return self._favorites_controller.build_favorite_name(state, existing_names, now)

    def load_selected_favorite(
        self,
        *,
        viewport: FractalViewportWidget | None,
        params_panel: FractalParamsPanel | None,
        selected_row: Any,
        load_row: Callable[[Any], None],
    ) -> None:
        if viewport is None or params_panel is None or selected_row is None:
            return
        load_row(selected_row)

    def delete_selected_favorite(
        self,
        *,
        selected_row,
        rows,
        favorites: list[dict],
        scroll_layout,
        persist_favorites: Callable[[], None],
    ):
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
        row: Any,
        favorites: list[dict],
        rows: list[Any],
        viewport: FractalViewportWidget | None,
        params_panel: FractalParamsPanel | None,
        editor: ColorCubeEditor | None,
        preview_palette: PalettePreviewWidget | None,
        apply_aspect_ratio_mode: Callable[[str], None],
        select_row: Callable[[Any], None],
        show_status: Callable[[str], None],
    ) -> None:
        self._favorites_controller.load_favorite_row(
            row=row,
            favorites=favorites,
            rows=rows,
            viewport=viewport,
            params_panel=params_panel,
            editor=editor,
            preview_palette=preview_palette,
            apply_aspect_ratio_mode=apply_aspect_ratio_mode,
            select_row=select_row,
            show_status=show_status,
        )