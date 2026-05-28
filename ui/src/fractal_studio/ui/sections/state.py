from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QComboBox, QLabel

from fractal_studio.ui.sections.panel_state import (
    MainWindowColormapState,
    MainWindowExportState,
    MainWindowFavoritesState,
    MainWindowPaletteState,
    MainWindowSidebarState,
    MainWindowViewportState,
)
from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget

if TYPE_CHECKING:
    from fractal_studio.backend import CoreBackend
    from fractal_studio.application.controllers.export_controller import (
        ExportController,
    )
    from fractal_studio.main_window import MainWindow
    from fractal_studio.main_window_factory import MainWindowContext
    from fractal_studio.ui.sections.sections import MainWindowSections
    from fractal_studio.persistence import FavoritesRepository, SettingsRepository
    from fractal_studio.application.workflows.favorites_workflow_coordinator import (
        FavoritesWorkflowCoordinator,
    )
    from fractal_studio.application.workflows.startup_coordinator import (
        WindowStartupCoordinator,
    )
    from fractal_studio.application.workflows.theme_workflow_coordinator import (
        ThemeWorkflowCoordinator,
    )
    from fractal_studio.application.coordinators.export_panel_coordinator import (
        ExportPanelCoordinator,
    )
    from fractal_studio.services.export_service import ExportService
    from fractal_studio.application.controllers.favorites_controller import (
        FavoritesController,
    )
    from fractal_studio.application.coordinators.favorites_panel_coordinator import (
        FavoritesPanelCoordinator,
    )
    from fractal_studio.application.coordinators.palette_panel_coordinator import (
        PalettePanelCoordinator,
    )
    from fractal_studio.application.coordinators.palette_preview_coordinator import (
        PalettePreviewCoordinator,
    )
    from fractal_studio.services.palette_service import PaletteWorkflowService
    from fractal_studio.application.coordinators.settings_dialog_coordinator import (
        SettingsDialogCoordinator,
    )
    from fractal_studio.services.settings_service import SettingsWorkflowService
    from fractal_studio.application.coordinators.sidebar_wiring_coordinator import (
        SidebarWiringCoordinator,
    )
    from fractal_studio.application.controllers.theme_controller import ThemeController


@dataclass
class MainWindowSectionsState:
    owner: MainWindow | None = None
    favorites_repo: FavoritesRepository | None = None
    settings_repo: SettingsRepository | None = None
    settings_service: SettingsWorkflowService | None = None
    startup: WindowStartupCoordinator | None = None
    favorites_controller: FavoritesController | None = None
    favorites_panel: FavoritesPanelCoordinator | None = None
    favorites_workflow: FavoritesWorkflowCoordinator | None = None
    sections: MainWindowSections | None = None
    theme_controller: ThemeController | None = None
    backend: CoreBackend | None = None
    export_service: ExportService | None = None
    palette_service: PaletteWorkflowService | None = None
    palette_panel: PalettePanelCoordinator | None = None
    palette_preview: PalettePreviewCoordinator | None = None
    sidebar_wiring: SidebarWiringCoordinator | None = None
    controller: ExportController | None = None
    export_panel: ExportPanelCoordinator | None = None
    settings_dialog: SettingsDialogCoordinator | None = None
    theme_workflow: ThemeWorkflowCoordinator | None = None
    backend_loaded: bool = False
    backend_profile: object | None = None
    hover_panel: QLabel | None = None

    def __post_init__(self) -> None:
        self._favorites_state = MainWindowFavoritesState(self)
        self._export_state = MainWindowExportState(self)
        self._viewport_state = MainWindowViewportState(self)
        self._sidebar_state = MainWindowSidebarState(self)
        self._palette_state = MainWindowPaletteState(self)
        self._colormap_state = MainWindowColormapState(self)

    @property
    def viewport(self) -> FractalViewportWidget | None:
        return self._viewport_state.viewport

    @viewport.setter
    def viewport(self, value: FractalViewportWidget | None) -> None:
        self._viewport_state.viewport = value

    @property
    def viewport_hint_label(self) -> QLabel | None:
        return self._viewport_state.viewport_hint_label

    @viewport_hint_label.setter
    def viewport_hint_label(self, value: QLabel | None) -> None:
        self._viewport_state.viewport_hint_label = value

    @property
    def aspect_ratio_combo(self) -> QComboBox | None:
        return self._viewport_state.aspect_ratio_combo

    @aspect_ratio_combo.setter
    def aspect_ratio_combo(self, value: QComboBox | None) -> None:
        self._viewport_state.aspect_ratio_combo = value

    @property
    def aspect_ratio_mode(self) -> str:
        return self._viewport_state.aspect_ratio_mode

    @aspect_ratio_mode.setter
    def aspect_ratio_mode(self, value: str) -> None:
        self._viewport_state.aspect_ratio_mode = value

    @property
    def params_panel(self) -> FractalParamsPanel | None:
        return self._sidebar_state.params_panel

    @params_panel.setter
    def params_panel(self, value: FractalParamsPanel | None) -> None:
        self._sidebar_state.params_panel = value

    @property
    def backend_state_label(self) -> QLabel | None:
        return self._sidebar_state.backend_state_label

    @backend_state_label.setter
    def backend_state_label(self, value: QLabel | None) -> None:
        self._sidebar_state.backend_state_label = value

    def bind(self, owner: MainWindow, context: MainWindowContext) -> None:
        self.owner = owner
        self.favorites_repo = context.favorites_repo
        self.settings_repo = context.settings_repo
        self.settings_service = context.settings_service
        self.startup = context.startup
        self.favorites_controller = context.favorites_controller
        self.favorites_panel = context.favorites_panel
        self.favorites_workflow = context.favorites_workflow
        self.sections = context.sections
        self.theme_controller = context.theme_controller
        self.backend = context.backend
        self.export_service = context.export_service
        self.palette_service = context.palette_service
        self.palette_panel = context.palette_panel
        self.palette_preview = context.palette_preview
        self.sidebar_wiring = context.sidebar_wiring
        self.controller = context.controller
        self.export_panel = context.export_panel
        self.settings_dialog = context.settings_dialog
        self.theme_workflow = context.theme_workflow
        self.backend_loaded = context.backend_loaded
        self.backend_profile = context.backend_profile
        self._viewport_state.bind_collaborators(
            controller=self.controller,
            export_panel=self.export_panel,
            refresh_export_presets=self._export_state.refresh_export_presets,
        )
        self._sidebar_state.bind_collaborators(
            sidebar_wiring=self.sidebar_wiring,
            viewport_getter=lambda: self.viewport,
            settings_service=self.settings_service,
            backend_loaded_getter=lambda: self.backend_loaded,
            backend_available_getter=lambda: (
                self.backend.available if self.backend is not None else False
            ),
        )
        self._favorites_state.bind_collaborators(
            favorites_controller=self.favorites_controller,
            favorites_panel=self.favorites_panel,
            favorites_workflow=self.favorites_workflow,
            favorites_repo=self.favorites_repo,
            owner=self.owner,
            hover_panel_getter=lambda: self.hover_panel,
            viewport_getter=lambda: self.viewport,
            params_panel_getter=lambda: self.params_panel,
            editor_getter=lambda: self._colormap_state.editor,
            preview_palette_getter=lambda: self._palette_state.preview_palette,
            apply_aspect_ratio_mode=self._viewport_state.apply_aspect_ratio_mode,
            aspect_ratio_mode_getter=lambda: self.aspect_ratio_mode,
        )
        self._palette_state.bind_collaborators(
            palette_preview=self.palette_preview,
            backend=self.backend,
            legacy_palette_size_getter=lambda: (
                None
                if self.backend_profile is None
                else self.backend_profile.legacy_palette_size
            ),
            editor_getter=lambda: self._colormap_state.editor,
        )
        self._colormap_state.bind_collaborators(
            palette_panel=self.palette_panel,
            backend=self.backend,
            owner=self.owner,
            legacy_palette_size_getter=lambda: (
                None
                if self.backend_profile is None
                else self.backend_profile.legacy_palette_size
            ),
        )
        self._export_state.bind_collaborators(
            export_panel=self.export_panel,
            controller=self.controller,
            owner=self.owner,
            viewport_getter=lambda: self.viewport,
            aspect_ratio_mode_getter=lambda: self.aspect_ratio_mode,
        )
        self.validate()

    def validate(self) -> None:
        required = [
            "owner",
            "favorites_repo",
            "settings_repo",
            "settings_service",
            "startup",
            "favorites_controller",
            "favorites_panel",
            "favorites_workflow",
            "sections",
            "theme_controller",
            "backend",
            "export_service",
            "palette_service",
            "palette_panel",
            "palette_preview",
            "sidebar_wiring",
            "controller",
            "export_panel",
            "settings_dialog",
            "theme_workflow",
        ]
        for name in required:
            if getattr(self, name, None) is None:
                raise RuntimeError(
                    f"MainWindowSectionsState.validate(): '{name}' was not bound. "
                    f"Call bind(owner, context) before validate()."
                )
