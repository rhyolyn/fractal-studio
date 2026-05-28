from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fractal_studio.backend import BackendProfile, CoreBackend, load_backend
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
from fractal_studio.application.controllers.favorites_controller import (
    FavoritesController,
)
from fractal_studio.application.coordinators.favorites_panel_coordinator import (
    FavoritesPanelCoordinator,
)
from fractal_studio.application.controllers.export_controller import (
    ExportController,
)
from fractal_studio.application.controllers.settings_controller import (
    SettingsController,
)
from fractal_studio.ui.sections.sections import MainWindowSections
from fractal_studio.ui.sections.mediator import (
    build_sections_ports,
)
from fractal_studio.ui.sections.ports import (
    MainWindowSectionsPorts,
)
from fractal_studio.application.coordinators.palette_panel_coordinator import (
    PalettePanelCoordinator,
)
from fractal_studio.application.coordinators.palette_preview_coordinator import (
    PalettePreviewCoordinator,
)
from fractal_studio.persistence import FavoritesRepository, SettingsRepository
from fractal_studio.application.coordinators.sidebar_wiring_coordinator import (
    SidebarWiringCoordinator,
)
from fractal_studio.application.coordinators.settings_dialog_coordinator import (
    SettingsDialogCoordinator,
)
from fractal_studio.services.export_service import ExportService
from fractal_studio.services.palette_service import PaletteWorkflowService
from fractal_studio.services.settings_service import SettingsWorkflowService
from fractal_studio.application.controllers.theme_controller import ThemeController
from fractal_studio.ui.presenters.favorite_hover_presenter import FavoriteHoverPresenter

if TYPE_CHECKING:
    from fractal_studio.main_window import MainWindow


@dataclass(frozen=True)
class MainWindowContext:
    favorites_repo: FavoritesRepository
    settings_repo: SettingsRepository
    settings_service: SettingsWorkflowService
    startup: WindowStartupCoordinator
    favorites_controller: FavoritesController
    favorites_panel: FavoritesPanelCoordinator
    favorites_workflow: FavoritesWorkflowCoordinator
    sections_ports: MainWindowSectionsPorts
    sections: MainWindowSections
    theme_controller: ThemeController
    backend: CoreBackend
    export_service: ExportService
    palette_service: PaletteWorkflowService
    palette_panel: PalettePanelCoordinator
    palette_preview: PalettePreviewCoordinator
    sidebar_wiring: SidebarWiringCoordinator
    controller: ExportController
    settings_controller: SettingsController
    export_panel: ExportPanelCoordinator
    settings_dialog: SettingsDialogCoordinator
    theme_workflow: ThemeWorkflowCoordinator
    backend_loaded: bool
    backend_profile: BackendProfile


def build_main_window_context(window: MainWindow) -> MainWindowContext:
    favorites_repo = FavoritesRepository(window._favorites_path)
    settings_repo = SettingsRepository(window._settings_path)
    settings_service = SettingsWorkflowService()
    startup = WindowStartupCoordinator(settings_repo, settings_service)
    favorites_controller = FavoritesController()
    favorites_panel = FavoritesPanelCoordinator(FavoriteHoverPresenter())
    favorites_workflow = FavoritesWorkflowCoordinator(
        favorites_controller,
        favorites_panel,
    )
    sections_ports = build_sections_ports(window)
    sections = MainWindowSections(sections_ports)
    theme_controller = ThemeController()
    backend = load_backend()
    export_service = ExportService(backend)
    palette_service = PaletteWorkflowService()
    palette_panel = PalettePanelCoordinator(palette_service)
    palette_preview = PalettePreviewCoordinator(favorites_controller)
    sidebar_wiring = SidebarWiringCoordinator()
    controller = ExportController(export_service, favorites_controller)
    settings_controller = SettingsController()
    export_panel = ExportPanelCoordinator(controller)
    settings_dialog = SettingsDialogCoordinator(settings_controller, settings_service)
    theme_workflow = ThemeWorkflowCoordinator(
        settings_dialog,
        theme_controller,
        settings_repo,
    )
    return MainWindowContext(
        favorites_repo=favorites_repo,
        settings_repo=settings_repo,
        settings_service=settings_service,
        startup=startup,
        favorites_controller=favorites_controller,
        favorites_panel=favorites_panel,
        favorites_workflow=favorites_workflow,
        sections_ports=sections_ports,
        sections=sections,
        theme_controller=theme_controller,
        backend=backend,
        export_service=export_service,
        palette_service=palette_service,
        palette_panel=palette_panel,
        palette_preview=palette_preview,
        sidebar_wiring=sidebar_wiring,
        controller=controller,
        settings_controller=settings_controller,
        export_panel=export_panel,
        settings_dialog=settings_dialog,
        theme_workflow=theme_workflow,
        backend_loaded=backend.available,
        backend_profile=backend.profile(),
    )


def create_main_window() -> MainWindow:
    from fractal_studio.main_window import MainWindow

    window = MainWindow()
    window.attach_context(build_main_window_context(window))
    window.initialize()
    return window
