from __future__ import annotations

from fractal_studio.editor import ColorCubeEditor, PalettePreviewWidget
from fractal_studio.application.controllers.favorites_controller import (
    FavoritesController,
)


class PalettePreviewCoordinator:
    """Coordinator for the palette preview panel. Owns preview refresh and control point summary display."""

    def __init__(self, favorites_controller: FavoritesController) -> None:
        self._favorites_controller = favorites_controller

    def update_control_summary(
        self, point_summary, control_points: list[tuple[int, int, int]]
    ) -> None:
        if point_summary is None:
            return
        point_summary.setText(f"{len(control_points)} control points")

    def update_palette_previews(
        self,
        *,
        palette: list[tuple[int, int, int]],
        editor: ColorCubeEditor | None,
        backend,
        legacy_palette_size: int,
        preview_palette: PalettePreviewWidget | None,
        preview_legacy: PalettePreviewWidget | None,
        palette_summary,
    ) -> None:
        self._favorites_controller.update_palette_previews(
            palette=palette,
            editor=editor,
            backend=backend,
            legacy_palette_size=legacy_palette_size,
            preview_palette=preview_palette,
            preview_legacy=preview_legacy,
            palette_summary=palette_summary,
        )
