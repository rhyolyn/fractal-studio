from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication

from fractal_studio.persistence import SettingsLoadResult, SettingsRepository
from fractal_studio.services.settings_service import SettingsWorkflowService
from fractal_studio.theme import ThemeSpec, apply_theme


@dataclass(frozen=True)
class WindowStartupState:
    theme_name: str
    theme_spec: ThemeSpec
    load_result: SettingsLoadResult


class WindowStartupCoordinator:
    def __init__(
        self,
        settings_repo: SettingsRepository,
        settings_service: SettingsWorkflowService,
    ) -> None:
        self._settings_repo = settings_repo
        self._settings_service = settings_service

    def bootstrap(
        self,
        *,
        application: QApplication | None,
    ) -> WindowStartupState:
        settings = self._settings_repo.load()
        theme_name = settings.settings.theme
        theme_spec = apply_theme(application, theme_name)
        return WindowStartupState(
            theme_name=theme_name,
            theme_spec=theme_spec,
            load_result=settings,
        )

    def compose_startup_message(
        self,
        *,
        backend_loaded: bool,
        startup_state: WindowStartupState,
        favorites_diagnostic: str = "",
    ) -> str:
        return self._settings_service.startup_status(
            backend_loaded=backend_loaded,
            load_result=startup_state.load_result,
            diagnostics=[startup_state.load_result.diagnostic, favorites_diagnostic],
        )
