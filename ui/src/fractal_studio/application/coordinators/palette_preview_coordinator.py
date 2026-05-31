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
            get_control_points=lambda: (
                list(editor.control_points) if editor is not None else []
            ),
            backend=backend,
            legacy_palette_size=legacy_palette_size,
            set_preview_palette=lambda pal: (
                preview_palette.set_palette(pal) if preview_palette is not None else None
            ),
            set_legacy_palette=lambda pal: (
                preview_legacy.set_palette(pal) if preview_legacy is not None else None
            ),
            set_summary_text=lambda txt: (
                palette_summary.setText(txt) if palette_summary is not None else None
            ),
        )
