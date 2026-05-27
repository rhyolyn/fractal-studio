from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import QApplication

from fractal_studio.persistence import SettingsRepository
from fractal_studio.settings_dialog_coordinator import SettingsDialogCoordinator
from fractal_studio.state import UiSettings
from fractal_studio.theme import ThemeSpec
from fractal_studio.theme_controller import ThemeController


class ThemeWorkflowCoordinator:
    def __init__(
        self,
        settings_dialog: SettingsDialogCoordinator,
        theme_controller: ThemeController,
        settings_repo: SettingsRepository,
    ) -> None:
        self._settings_dialog = settings_dialog
        self._theme_controller = theme_controller
        self._settings_repo = settings_repo

    def apply_theme_name(
        self,
        *,
        theme_name: str,
        persist: bool,
        current_theme: str,
        current_theme_spec: ThemeSpec,
        application: QApplication | None,
        refresh_dynamic_widgets,
    ) -> tuple[str, ThemeSpec]:
        theme_spec = current_theme_spec

        def apply_theme_to_app(name: str) -> None:
            nonlocal theme_spec
            theme_spec = self._theme_controller.apply_theme(application, name)

        updated_theme = self._settings_dialog.apply_theme_name(
            theme_name=theme_name,
            persist=persist,
            current_theme=current_theme,
            apply_theme_to_app=apply_theme_to_app,
            persist_theme=lambda name: self._settings_repo.save(UiSettings(theme=name)),
            refresh_dynamic_widgets=refresh_dynamic_widgets,
        )
        return updated_theme, theme_spec

    def open_settings(
        self,
        *,
        parent,
        current_theme: str,
        current_theme_spec: ThemeSpec,
        dialog_factory: Callable[[str, Any], Any],
        application: QApplication | None,
        refresh_dynamic_widgets,
    ) -> tuple[str, ThemeSpec]:
        updated_theme = current_theme
        updated_theme_spec = current_theme_spec

        def apply_theme_name(theme_name: str, persist: bool) -> None:
            nonlocal updated_theme
            nonlocal updated_theme_spec
            updated_theme, updated_theme_spec = self.apply_theme_name(
                theme_name=theme_name,
                persist=persist,
                current_theme=updated_theme,
                current_theme_spec=updated_theme_spec,
                application=application,
                refresh_dynamic_widgets=refresh_dynamic_widgets,
            )

        self._settings_dialog.open_settings_dialog(
            parent=parent,
            current_theme=current_theme,
            dialog_factory=dialog_factory,
            apply_theme_name=apply_theme_name,
        )
        return updated_theme, updated_theme_spec