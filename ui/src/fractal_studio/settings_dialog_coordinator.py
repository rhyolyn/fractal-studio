from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fractal_studio.main_window_controller import MainWindowController
from fractal_studio.settings_service import SettingsWorkflowService


class SettingsDialogCoordinator:
    def __init__(self, controller: MainWindowController, settings_service: SettingsWorkflowService) -> None:
        self._controller = controller
        self._settings_service = settings_service

    def open_settings_dialog(
        self,
        *,
        parent,
        current_theme: str,
        dialog_factory: Callable[[str, Any], Any],
        apply_theme_name: Callable[[str, bool], None],
    ) -> None:
        self._controller.open_settings_dialog(
            parent=parent,
            current_theme=current_theme,
            dialog_factory=dialog_factory,
            apply_theme_name=apply_theme_name,
        )

    def apply_theme_name(
        self,
        *,
        theme_name: str,
        persist: bool,
        current_theme: str,
        apply_theme_to_app: Callable[[str], None],
        persist_theme: Callable[[str], None],
        refresh_dynamic_widgets: Callable[[], None],
    ) -> str:
        updated_theme = self._settings_service.apply_theme_name(
            theme_name=theme_name,
            persist=persist,
            current_theme=current_theme,
            apply_theme_to_app=apply_theme_to_app,
            persist_theme=persist_theme,
        )
        refresh_dynamic_widgets()
        return updated_theme
