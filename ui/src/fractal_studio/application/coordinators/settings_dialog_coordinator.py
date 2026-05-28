from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from fractal_studio.application.controllers.settings_controller import (
    SettingsController,
    SettingsDialogFactory,
)
from fractal_studio.services.settings_service import SettingsWorkflowService

if TYPE_CHECKING:
    from fractal_studio.main_window import MainWindow


class SettingsDialogCoordinator:
    """Coordinator for the settings dialog. Owns dialog lifecycle and theme preview vs. persist logic."""

    def __init__(
        self,
        controller: SettingsController,
        settings_service: SettingsWorkflowService,
    ) -> None:
        self._controller = controller
        self._settings_service = settings_service

    def open_settings_dialog(
        self,
        *,
        parent: MainWindow,
        current_theme: str,
        dialog_factory: SettingsDialogFactory,
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
