from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget

from fractal_studio.theme import get_theme


class FavoriteRowStylePresenter:
    def apply_visual_state(
        self,
        row: QWidget,
        thumb_label: QLabel,
        name_label: QLabel,
        *,
        selected: bool,
        hovered: bool,
    ) -> None:
        theme = getattr(row.window(), "_theme_spec", get_theme("light"))
        if selected:
            row.setStyleSheet(
                "border-radius: 4px; "
                f"border-left: 4px solid {theme.selected_border}; "
                f"background-color: {theme.selection_bg};"
            )
            thumb_label.setStyleSheet(f"border: 2px solid {theme.selected_border}; border-radius: 3px;")
            name_label.setStyleSheet("font-weight: 600;")
        elif hovered:
            row.setStyleSheet(
                "border-radius: 4px; "
                f"border-left: 4px solid {theme.hover_border}; "
                f"background-color: {theme.hover_bg};"
            )
            thumb_label.setStyleSheet(f"border: 2px solid {theme.hover_border}; border-radius: 3px;")
            name_label.setStyleSheet("")
        else:
            row.setStyleSheet("border-radius: 4px; border-left: 4px solid transparent; background-color: transparent;")
            thumb_label.setStyleSheet("border: 2px solid transparent; border-radius: 3px;")
            name_label.setStyleSheet("")
        row.update()
