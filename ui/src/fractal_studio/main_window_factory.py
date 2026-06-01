from __future__ import annotations

from pathlib import Path
from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread
from fractal_studio.backend import CoreBackend, load_backend
from fractal_studio.ui.workers.render_worker import RenderWorker
from fractal_studio.ui.workers.render_scheduler import RenderScheduler
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
from fractal_studio.ui.sections.mediator import build_sections_ports
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
from fractal_studio.ui.sections.panel_state import (
    MainWindowColormapState,
    MainWindowExportState,
    MainWindowFavoritesState,
    MainWindowPaletteState,
    MainWindowSidebarState,
    MainWindowViewportState,
)
from fractal_studio.ui.sections.state import MainWindowSectionsState
from fractal_studio.viewport import FractalViewportWidget

_FAVORITES_PATH = Path.home() / ".fractal_studio" / "favorites.json"
_SETTINGS_PATH = Path.home() / ".fractal_studio" / "settings.json"


def create_main_window():
    from fractal_studio.main_window import MainWindow

    # ── 1. Build repos, services, controllers, coordinators, backend ──
    favorites_repo = FavoritesRepository(_FAVORITES_PATH)
    settings_repo = SettingsRepository(_SETTINGS_PATH)
    settings_service = SettingsWorkflowService()
    theme_controller = ThemeController()
    startup = WindowStartupCoordinator(settings_repo, settings_service, theme_controller)
    favorites_controller = FavoritesController()
    favorites_panel = FavoritesPanelCoordinator(FavoriteHoverPresenter())
    favorites_workflow = FavoritesWorkflowCoordinator(
        favorites_controller, favorites_panel
    )
    backend = load_backend()
    export_service = ExportService(backend)
    palette_service = PaletteWorkflowService()
    palette_panel = PalettePanelCoordinator(palette_service)
    palette_preview = PalettePreviewCoordinator(favorites_controller)
    sidebar_wiring = SidebarWiringCoordinator()
    export_controller = ExportController(export_service)
    settings_controller = SettingsController()
    export_panel = ExportPanelCoordinator(export_controller)
    settings_dialog = SettingsDialogCoordinator(settings_controller, settings_service)
    theme_workflow = ThemeWorkflowCoordinator(
        settings_dialog, theme_controller, settings_repo
    )
    backend_loaded = backend.available
    backend_profile = backend.profile()

    # ── Async render thread ──
    render_scheduler = RenderScheduler()
    render_worker = RenderWorker(backend)
    render_thread = QThread()
    render_worker.moveToThread(render_thread)
    render_scheduler.render_requested.connect(render_worker.do_render)
    render_worker.render_complete.connect(render_scheduler._on_result)
    render_thread.start()

    # ── 2. Create MainWindow shell so status bar exists ──
    window = MainWindow()
    on_status: Callable[[str], None] = window.statusBar().showMessage

    # ── 3. Build panel states with explicit collaborators ──
    legacy_size: Callable[[], int | None] = (
        lambda: backend_profile.legacy_palette_size
    )

    # Export state built first (needs setters for circular deps)
    export_state = MainWindowExportState(
        export_panel=export_panel,
        controller=export_controller,
        on_status=on_status,
    )
    # Viewport state built second — passes export_state.refresh_export_presets
    viewport_state = MainWindowViewportState(
        controller=export_controller,
        export_panel=export_panel,
        refresh_export_presets=export_state.refresh_export_presets,
    )
    # Wire circular getters via setters
    export_state.set_viewport_getter(lambda: viewport_state.viewport)
    export_state.set_aspect_ratio_mode_getter(lambda: viewport_state.aspect_ratio_mode)

    colormap_state = MainWindowColormapState(
        palette_panel=palette_panel,
        backend=backend,
        on_status=on_status,
        legacy_palette_size_getter=legacy_size,
    )
    palette_state = MainWindowPaletteState(
        palette_preview=palette_preview,
        backend=backend,
        legacy_palette_size_getter=legacy_size,
        editor_getter=lambda: colormap_state.editor,
    )
    sidebar_state = MainWindowSidebarState(
        sidebar_wiring=sidebar_wiring,
        viewport_getter=lambda: viewport_state.viewport,
        settings_service=settings_service,
        backend_loaded_getter=lambda: backend_loaded,
        backend_available_getter=lambda: backend.available,
    )
    favorites_state = MainWindowFavoritesState(
        favorites_controller=favorites_controller,
        favorites_panel=favorites_panel,
        favorites_workflow=favorites_workflow,
        favorites_repo=favorites_repo,
        on_status=on_status,
        hover_panel_getter=lambda: window.hover_panel,
        viewport_getter=lambda: viewport_state.viewport,
        params_panel_getter=lambda: sidebar_state.params_panel,
        editor_getter=lambda: colormap_state.editor,
        preview_palette_getter=lambda: palette_state.preview_palette,
        apply_aspect_ratio_mode=viewport_state.apply_aspect_ratio_mode,
        aspect_ratio_mode_getter=lambda: viewport_state.aspect_ratio_mode,
    )

    # ── 4. Build sections state container and validate ──
    sections_state = MainWindowSectionsState(
        viewport=viewport_state,
        sidebar=sidebar_state,
        palette=palette_state,
        colormap=colormap_state,
        favorites=favorites_state,
        export=export_state,
    )
    sections_state.validate()
    render_scheduler.render_ready.connect(viewport_state._on_render_ready)

    # ── 5. Build section adapters and sections ──
    sections_ports = build_sections_ports(sections_state, on_status, backend, backend_profile, render_scheduler)
    sections = MainWindowSections(sections_ports)

    # ── 6. Initialize window ──
    window.initialize_sections(
        sections=sections,
        sections_state=sections_state,
        favorites_repo=favorites_repo,
        settings_repo=settings_repo,
        settings_controller=settings_controller,
        settings_service=settings_service,
        startup=startup,
        favorites_controller=favorites_controller,
        favorites_panel=favorites_panel,
        favorites_workflow=favorites_workflow,
        theme_controller=theme_controller,
        backend=backend,
        backend_loaded=backend_loaded,
        backend_profile=backend_profile,
        theme_workflow=theme_workflow,
    )

    import atexit
    from PySide6.QtWidgets import QApplication

    def _stop_render_thread() -> None:
        render_thread.quit()
        render_thread.wait()

    app = QApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(_stop_render_thread)
    atexit.register(_stop_render_thread)

    return window
