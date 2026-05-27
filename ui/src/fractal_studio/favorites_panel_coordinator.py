from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout


class FavoriteRowLike(Protocol):
    def set_selected(self, selected: bool) -> None:
        ...

    def deleteLater(self) -> None:
        ...


class FavoritesPanelCoordinator:
    def __init__(self, hover_presenter) -> None:
        self._hover_presenter = hover_presenter

    def build_row(
        self,
        *,
        favorite: dict,
        hover_panel: QLabel,
        on_select: Callable[[Any], None],
        on_activate: Callable[[Any], None],
        row_factory: Callable[..., Any],
        decode_thumbnail: Callable[[str], QPixmap],
        placeholder_pixmap: Callable[[], QPixmap],
    ) -> Any:
        pixmap = self._resolve_thumbnail(favorite, decode_thumbnail, placeholder_pixmap)
        return row_factory(
            pixmap,
            favorite,
            hover_panel,
            on_select,
            on_activate,
            hover_presenter=self._hover_presenter,
        )

    def append_row(self, row: Any, rows: list[Any], scroll_layout: QVBoxLayout) -> None:
        rows.append(row)
        # Insert before the trailing stretch (always last item).
        scroll_layout.insertWidget(len(rows) - 1, row)

    def select_row(self, selected_row: FavoriteRowLike | None, row: FavoriteRowLike) -> FavoriteRowLike:
        if selected_row is not None:
            selected_row.set_selected(False)
        row.set_selected(True)
        return row

    def delete_selected(
        self,
        *,
        selected_row: FavoriteRowLike | None,
        rows: list[FavoriteRowLike],
        favorites: list[dict],
        scroll_layout: QVBoxLayout,
    ) -> FavoriteRowLike | None:
        if selected_row is None:
            return selected_row
        idx = rows.index(selected_row)
        favorites.pop(idx)
        row = rows.pop(idx)
        scroll_layout.removeWidget(row)
        row.deleteLater()
        return None

    def _resolve_thumbnail(
        self,
        favorite: dict,
        decode_thumbnail: Callable[[str], QPixmap],
        placeholder_pixmap: Callable[[], QPixmap],
    ) -> QPixmap:
        thumbnail = favorite.get("thumbnail")
        if not thumbnail:
            return placeholder_pixmap()

        try:
            pixmap = decode_thumbnail(str(thumbnail))
            return pixmap if not pixmap.isNull() else placeholder_pixmap()
        except Exception:
            return placeholder_pixmap()
