from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from fractal_studio.backend import BackendProfile, CoreBackend
from fractal_studio.editor import ColorCubeEditor
from fractal_studio.persistence import FavoritesRepository, SettingsRepository
from fractal_studio.ui.sections.sections import MainWindowSections
from fractal_studio.ui.sections.state import MainWindowSectionsState
from fractal_studio.theme import ThemeSpec, get_theme
from fractal_studio.application.controllers.favorites_controller import FavoritesController
from fractal_studio.application.controllers.settings_controller import SettingsController
from fractal_studio.application.controllers.theme_controller import ThemeController
from fractal_studio.application.coordinators.favorites_panel_coordinator import FavoritesPanelCoordinator
from fractal_studio.application.workflows.favorites_workflow_coordinator import FavoritesWorkflowCoordinator
from fractal_studio.application.workflows.startup_coordinator import WindowStartupCoordinator, WindowStartupState
from fractal_studio.application.workflows.theme_workflow_coordinator import ThemeWorkflowCoordinator
from fractal_studio.services.settings_service import SettingsWorkflowService
from fractal_studio.ui.dialogs.appearance_settings_dialog import (
    AppearanceSettingsDialog,
)
from fractal_studio.viewport import FractalViewportWidget

_FAVORITES_PATH = Path.home() / ".fractal_studio" / "favorites.json"
_SETTINGS_PATH = Path.home() / ".fractal_studio" / "settings.json"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._init_window_state()
        self._configure_window_frame()

    def _init_window_state(self) -> None:
        self._favorites_path = _FAVORITES_PATH
        self._settings_path = _SETTINGS_PATH
        self.hover_panel: QLabel | None = None
        self._theme_name = "light"
        self._theme_spec: ThemeSpec = get_theme(self._theme_name)
        self._startup_sidebar_collapsed: dict[str, bool] = {}

    def initialize_sections(
        self,
        *,
        sections: MainWindowSections,
        sections_state: MainWindowSectionsState,
        favorites_repo: FavoritesRepository,
        settings_repo: SettingsRepository,
        settings_controller: SettingsController,
        settings_service: SettingsWorkflowService,
        startup: WindowStartupCoordinator,
        favorites_controller: FavoritesController,
        favorites_panel: FavoritesPanelCoordinator,
        favorites_workflow: FavoritesWorkflowCoordinator,
        theme_controller: ThemeController,
        backend: CoreBackend,
        backend_loaded: bool,
        backend_profile: BackendProfile,
        theme_workflow: ThemeWorkflowCoordinator,
    ) -> None:
        self._sections = sections
        self._sections_state = sections_state
        self._favorites_repo = favorites_repo
        self._settings_repo = settings_repo
        self._settings_controller = settings_controller
        self._settings_service = settings_service
        self._startup = startup
        self._favorites_controller = favorites_controller
        self._favorites_panel = favorites_panel
        self._favorites_workflow = favorites_workflow
        self._theme_controller = theme_controller
        self.backend = backend
        self.backend_loaded = backend_loaded
        self.backend_profile = backend_profile
        self._theme_workflow = theme_workflow
        self.initialize()

    def initialize(self) -> None:
        startup = self._bootstrap_startup()
        self._init_hover_panel()
        self._finalize_startup(startup)

    def _configure_window_frame(self) -> None:
        self.setWindowTitle("Fractal Studio")
        self.resize(1500, 940)

    @property
    def editor(self) -> ColorCubeEditor | None:
        return self._sections_state.colormap.editor

    @property
    def viewport(self) -> FractalViewportWidget | None:
        return self._sections_state.viewport.viewport

    @property
    def viewport_hint_label(self) -> QLabel | None:
        return self._sections_state.viewport.viewport_hint_label

    def _bootstrap_startup(self) -> WindowStartupState:
        startup = self._startup.bootstrap(
            application=QApplication.instance(),
        )
        self._theme_name = startup.theme_name
        self._theme_spec = startup.theme_spec
        return startup

    def _init_hover_panel(self) -> None:
        self.hover_panel = QLabel(self)
        self.hover_panel.setObjectName("hoverPanel")
        self.hover_panel.hide()

    def _finalize_startup(self, startup: WindowStartupState) -> None:
        # Export always starts expanded for discoverability; ignore any saved collapsed state.
        self._startup_sidebar_collapsed = {k: v for k, v in startup.sidebar_collapsed.items() if k != "export"}
        self._sections.set_theme(startup.theme_spec)       # must precede _build_layout
        self.setCentralWidget(self._build_layout())
        self._theme_controller.refresh_dynamic_widgets(
            self.hover_panel,
            self._sections_state.favorites.fav_rows,
            viewport_well=self._sections.viewport_well,
        )
        self.statusBar().showMessage(
            self._startup.compose_startup_message(
                backend_loaded=self.backend_loaded,
                startup_state=startup,
                favorites_diagnostic=self._favorites_repo.last_load_diagnostic,
            )
        )

    def _build_layout(self) -> QWidget:
        splitter = self._build_main_splitter()

        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(
            self._sections.build_header(self.backend_profile, self._open_settings)
        )
        layout.addWidget(splitter)
        container.setLayout(layout)
        return container

    def _build_main_splitter(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)  # match workspace grid spacing
        splitter.addWidget(self._sections.build_workspace())
        splitter.addWidget(self._sections.build_sidebar(
            sidebar_collapsed=self._startup_sidebar_collapsed,
            on_section_collapsed=self._on_section_collapsed,
        ))
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1200, 300])
        return splitter

    def _on_section_collapsed(self, section_key: str, collapsed: bool) -> None:
        self._settings_controller.save_sidebar_collapsed(
            self._settings_repo, section_key, collapsed
        )

    def _open_settings(self) -> None:
        self._theme_name, self._theme_spec = self._theme_workflow.open_settings(
            parent=self,
            current_theme=self._theme_name,
            current_theme_spec=self._theme_spec,
            dialog_factory=lambda theme, parent: AppearanceSettingsDialog(
                theme, parent,
                backend_profile=self.backend_profile,
                backend_loaded=self.backend_loaded,
            ),
            application=QApplication.instance(),
            refresh_dynamic_widgets=lambda: (
                self._theme_controller.refresh_dynamic_widgets(
                    self.hover_panel,
                    self._sections_state.favorites.fav_rows,
                    viewport_well=self._sections.viewport_well,
                )
            ),
        )
