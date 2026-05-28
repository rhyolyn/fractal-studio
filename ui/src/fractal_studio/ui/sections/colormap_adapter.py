from __future__ import annotations

from fractal_studio.editor import ColorCubeEditor
from fractal_studio.ui.sections.base import (
    _BasePortsAdapter,
    _FavoriteActionsMixin,
)


class ColormapPanelPortsAdapter(_FavoriteActionsMixin, _BasePortsAdapter):
    def set_editor(self, editor: ColorCubeEditor) -> None:
        self._state._colormap_state.set_editor(editor)

    def update_palette_previews(self, palette) -> None:
        self._state._palette_state.update_palette_previews(palette)

    def update_control_summary(self, points) -> None:
        self._state._palette_state.update_control_summary(points)

    def load_palette_json(self) -> None:
        self._state._colormap_state.load_palette_json()

    def export_legacy_map(self) -> None:
        self._state._colormap_state.export_legacy_map()
