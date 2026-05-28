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

from fractal_studio.editor import ColorCubeEditor
from fractal_studio.main_window_factory import MainWindowContext
from fractal_studio.ui.sections.state import (
    MainWindowSectionsState,
)
from fractal_studio.theme import ThemeSpec, get_theme
from fractal_studio.application.workflows.startup_coordinator import WindowStartupState
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
        self._sections_state = MainWindowSectionsState()
        self._hover_panel: QLabel | None = None
        self._theme_name = "light"
        self._theme_spec: ThemeSpec = get_theme(self._theme_name)

    def attach_context(self, context: MainWindowContext) -> None:
        self._sections_state.bind(self, context)
        self._favorites_repo = context.favorites_repo
        self._settings_repo = context.settings_repo
        self._settings_service = context.settings_service
        self._startup = context.startup
        self._favorites_controller = context.favorites_controller
        self._favorites_panel = context.favorites_panel
        self._favorites_workflow = context.favorites_workflow
        self._sections_ports = context.sections_ports
        self._sections = context.sections
        self._theme_controller = context.theme_controller
        self.backend = context.backend
        self._export_service = context.export_service
        self._palette_service = context.palette_service
        self._palette_panel = context.palette_panel
        self._palette_preview = context.palette_preview
        self._sidebar_wiring = context.sidebar_wiring
        self._controller = context.controller
        self._export_panel = context.export_panel
        self._settings_dialog = context.settings_dialog
        self._theme_workflow = context.theme_workflow
        self.backend_loaded = context.backend_loaded
        self.backend_profile = context.backend_profile

    def initialize(self) -> None:
        startup = self._bootstrap_startup()
        self._init_hover_panel()
        self._finalize_startup(startup)

    def _configure_window_frame(self) -> None:
        self.setWindowTitle("Fractal Studio")
        self.resize(1500, 940)

    @property
    def editor(self) -> ColorCubeEditor | None:
        return self._sections_state._colormap_state.editor

    @property
    def viewport(self) -> FractalViewportWidget | None:
        return self._sections_state.viewport

    @property
    def viewport_hint_label(self) -> QLabel | None:
        return self._sections_state.viewport_hint_label

    def _bootstrap_startup(self) -> WindowStartupState:
        startup = self._startup.bootstrap(
            application=QApplication.instance(),
        )
        self._theme_name = startup.theme_name
        self._theme_spec = startup.theme_spec
        return startup

    def _init_hover_panel(self) -> None:
        self._hover_panel = QLabel(self)
        self._hover_panel.setObjectName("hoverPanel")
        self._hover_panel.hide()
        self._sections_state.hover_panel = self._hover_panel

    def _finalize_startup(self, startup: WindowStartupState) -> None:
        self.setCentralWidget(self._build_layout())
        self._theme_controller.refresh_dynamic_widgets(
            self._hover_panel, self._sections_state._favorites_state.fav_rows
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
        splitter.addWidget(self._sections.build_workspace())
        splitter.addWidget(self._sections.build_sidebar())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1200, 300])
        return splitter

    def _open_settings(self) -> None:
        self._theme_name, self._theme_spec = self._theme_workflow.open_settings(
            parent=self,
            current_theme=self._theme_name,
            current_theme_spec=self._theme_spec,
            dialog_factory=lambda theme, parent: AppearanceSettingsDialog(
                theme, parent
            ),
            application=QApplication.instance(),
            refresh_dynamic_widgets=lambda: (
                self._theme_controller.refresh_dynamic_widgets(
                    self._hover_panel,
                    self._sections_state._favorites_state.fav_rows,
                )
            ),
        )
