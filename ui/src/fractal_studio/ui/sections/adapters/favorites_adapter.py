from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from fractal_studio.ui.sections.adapters.base import (
    _BasePortsAdapter,
    _FavoriteActionsMixin,
)
from fractal_studio.state import FavoriteSnapshot


class FavoritesPanelPortsAdapter(_FavoriteActionsMixin, _BasePortsAdapter):
    def set_favorites_scroll_container(
        self, widget: QWidget, layout: QVBoxLayout
    ) -> None:
        self._state.favorites.set_favorites_scroll_container(widget, layout)

    def load_favorites(self) -> list[FavoriteSnapshot]:
        return self._state.favorites.load_favorites()

    def add_favorite_row(self, favorite: FavoriteSnapshot) -> None:
        self._state.favorites.add_favorite_row(favorite)

    def delete_selected_favorite(self) -> None:
        self._state.favorites.delete_selected_favorite()
