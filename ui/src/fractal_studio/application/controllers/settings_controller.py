from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from PySide6.QtWidgets import QDialog, QWidget


class _PreviewSignalLike(Protocol):
    def connect(self, slot: Callable[[str], None]) -> Any: ...


class SettingsDialogLike(Protocol):
    @property
    def theme_preview_requested(self) -> _PreviewSignalLike: ...

    def exec(self) -> int: ...

    def selected_theme(self) -> str: ...


SettingsDialogFactory = Callable[[str, QWidget], SettingsDialogLike]


class SettingsController:
    """Controller for settings dialog lifecycle.

    Owns the theme preview vs. persist decision when a settings dialog
    is opened.
    """

    def open_settings_dialog(
        self,
        parent: QWidget,
        current_theme: str,
        dialog_factory: SettingsDialogFactory,
        apply_theme_name: Callable[[str, bool], None],
    ) -> None:
        original_theme = current_theme
        dialog = dialog_factory(current_theme, parent)
        dialog.theme_preview_requested.connect(
            lambda theme_name: apply_theme_name(theme_name, False)
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            apply_theme_name(dialog.selected_theme(), True)
        elif dialog.selected_theme() != original_theme:
            apply_theme_name(original_theme, False)
