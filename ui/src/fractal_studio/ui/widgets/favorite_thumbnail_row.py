from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from fractal_studio.ui.presenters.favorite_hover_presenter import FavoriteHoverPresenter
from fractal_studio.ui.presenters.favorite_row_style_presenter import (
    FavoriteRowStylePresenter,
)


class FavoriteThumbnailRow(QWidget):
    def __init__(
        self,
        pixmap: QPixmap,
        fav: dict,
        hover_panel: QLabel,
        on_select: Callable[[Any], None],
        on_activate: Callable[[Any], None] | None = None,
        hover_presenter: FavoriteHoverPresenter | None = None,
        style_presenter: FavoriteRowStylePresenter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._fav = fav
        self._hover_panel = hover_panel
        self._hover_presenter = hover_presenter or FavoriteHoverPresenter()
        self._style_presenter = style_presenter or FavoriteRowStylePresenter()
        self._on_select = on_select
        self._on_activate = on_activate if on_activate is not None else on_select
        self._selected = False
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout()
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(8)

        self._thumb_label = QLabel()
        self._thumb_label.setObjectName("favoriteThumb")
        self._thumb_label.setFixedSize(48, 36)
        self._thumb_label.setPixmap(
            pixmap.scaled(
                48,
                36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        self._name_label = QLabel(fav["name"])
        self._name_label.setObjectName("favoriteName")
        self._name_label.setMinimumWidth(0)
        self._name_label.setWordWrap(False)

        self._thumb_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._name_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )

        layout.addWidget(self._thumb_label)
        layout.addWidget(self._name_label, 1)
        self.setLayout(layout)
        self._thumb_label.setStyleSheet(
            "border: 2px solid transparent; border-radius: 3px;"
        )
        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_visual_state()

    def _set_hovered(self, hovered: bool) -> None:
        self._hovered = hovered
        self._apply_visual_state()

    def _apply_visual_state(self) -> None:
        self._style_presenter.apply_visual_state(
            self,
            self._thumb_label,
            self._name_label,
            selected=self._selected,
            hovered=self._hovered,
        )

    def mousePressEvent(self, event) -> None:
        self._on_select(self)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self._on_select(self)
        self._on_activate(self)
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event) -> None:
        self._set_hovered(True)
        self._hover_presenter.show_for_row(self, self._hover_panel, self._fav)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_hovered(False)
        self._hover_presenter.hide(self._hover_panel)
        super().leaveEvent(event)
