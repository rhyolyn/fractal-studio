from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import QApplication

from fractal_studio.theme import ThemeSpec, apply_theme


class ThemeController:
    def __init__(self) -> None:
        self._current_theme: ThemeSpec | None = None

    def apply_theme(self, app: QApplication | None, theme_name: str) -> ThemeSpec:
        spec = apply_theme(app, theme_name)
        self._current_theme = spec
        return spec

    def refresh_dynamic_widgets(
        self,
        hover_panel,
        favorite_rows: Iterable,
        viewport_well=None,
    ) -> None:
        if hover_panel is not None:
            hover_panel.style().unpolish(hover_panel)
            hover_panel.style().polish(hover_panel)

        for row in favorite_rows:
            apply_visual_state = getattr(row, "_apply_visual_state", None)
            if callable(apply_visual_state):
                apply_visual_state()

        if viewport_well is not None and self._current_theme is not None:
            viewport_well.set_theme(self._current_theme)
