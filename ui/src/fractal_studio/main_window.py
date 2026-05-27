from __future__ import annotations

from pathlib import Path

_FAVORITES_PATH = Path.home() / ".fractal_studio" / "favorites.json"
_SETTINGS_PATH = Path.home() / ".fractal_studio" / "settings.json"

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QLabel,
    QMainWindow,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from fractal_studio.appearance_settings_dialog import AppearanceSettingsDialog
from fractal_studio.backend import BackendProfile, load_backend
from fractal_studio.custom_resolution_dialog import CustomResolutionDialog
from fractal_studio.editor import ColorCubeEditor, PalettePreviewWidget
from fractal_studio.export_panel_coordinator import ExportPanelCoordinator
from fractal_studio.export_service import ExportService
from fractal_studio.favorite_hover_presenter import FavoriteHoverPresenter
from fractal_studio.favorite_thumbnail_row import FavoriteThumbnailRow
from fractal_studio.favorites_controller import FavoritesController
from fractal_studio.favorites_panel_coordinator import FavoritesPanelCoordinator
from fractal_studio.favorites_workflow_coordinator import FavoritesWorkflowCoordinator
from fractal_studio.main_window_controller import MainWindowController
from fractal_studio.main_window_sections import MainWindowSections
from fractal_studio.main_window_sections_mediator import build_main_window_sections_ports
from fractal_studio.palette_panel_coordinator import PalettePanelCoordinator
from fractal_studio.palette_preview_coordinator import PalettePreviewCoordinator
from fractal_studio.palette_service import PaletteWorkflowService
from fractal_studio.persistence import FavoritesRepository, SettingsRepository
from fractal_studio.sidebar_wiring_coordinator import SidebarWiringCoordinator
from fractal_studio.settings_dialog_coordinator import SettingsDialogCoordinator
from fractal_studio.settings_service import SettingsWorkflowService
from fractal_studio.startup_coordinator import WindowStartupCoordinator
from fractal_studio.thumbnail_utils import decode_thumbnail, placeholder_pixmap
from fractal_studio.theme import ThemeSpec, get_theme
from fractal_studio.theme_controller import ThemeController
from fractal_studio.theme_workflow_coordinator import ThemeWorkflowCoordinator
from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget
from fractal_studio.placeholder_panel import PlaceholderPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._init_collaborators()
        self._init_window_state()
        self._configure_window_frame()

        startup = self._bootstrap_startup()
        self._init_hover_panel()
        self._finalize_startup(startup)

    def _init_collaborators(self) -> None:
        self._favorites_repo = FavoritesRepository(_FAVORITES_PATH)
        self._settings_repo = SettingsRepository(_SETTINGS_PATH)
        self._settings_service = SettingsWorkflowService()
        self._startup = WindowStartupCoordinator(self._settings_repo, self._settings_service)
        self._favorites_controller = FavoritesController()
        self._favorites_panel = FavoritesPanelCoordinator(FavoriteHoverPresenter())
        self._favorites_workflow = FavoritesWorkflowCoordinator(
            self._favorites_controller,
            self._favorites_panel,
        )
        self._sections_ports = build_main_window_sections_ports(self)
        self._sections = MainWindowSections(self._sections_ports)
        self._theme_controller = ThemeController()
        self.backend = load_backend()
        self._export_service = ExportService(self.backend)
        self._palette_service = PaletteWorkflowService()
        self._palette_panel = PalettePanelCoordinator(self._palette_service)
        self._palette_preview = PalettePreviewCoordinator(self._favorites_controller)
        self._sidebar_wiring = SidebarWiringCoordinator()
        self._controller = MainWindowController(self._export_service, self._favorites_controller)
        self._export_panel = ExportPanelCoordinator(self._controller)
        self._settings_dialog = SettingsDialogCoordinator(self._controller, self._settings_service)
        self._theme_workflow = ThemeWorkflowCoordinator(
            self._settings_dialog,
            self._theme_controller,
            self._settings_repo,
        )
        self.backend_loaded = self.backend.available
        self.backend_profile = self.backend.profile()

    def _init_window_state(self) -> None:
        self.editor: ColorCubeEditor | None = None
        self.viewport: FractalViewportWidget | None = None
        self.params_panel: FractalParamsPanel | None = None
        self.preview_palette: PalettePreviewWidget | None = None
        self.preview_legacy: PalettePreviewWidget | None = None
        self.point_summary: QLabel | None = None
        self.palette_summary: QLabel | None = None
        self.backend_state_label: QLabel | None = None
        self.viewport_hint_label: QLabel | None = None
        self._aspect_ratio_combo: QComboBox | None = None
        self._aspect_ratio_mode: str = "square"
        self._favorites: list[dict] = []
        self._export_combo: QComboBox | None = None
        self._export_presets: list[tuple[str, int, int]] = []
        self._custom_width: int = 1080
        self._custom_height: int = 1080
        self._custom_width_box: QSpinBox | None = None
        self._custom_height_box: QSpinBox | None = None
        self._selected_row: FavoriteThumbnailRow | None = None
        self._fav_rows: list[FavoriteThumbnailRow] = []
        self._fav_scroll_layout: QVBoxLayout | None = None
        self._theme_name = "light"
        self._theme_spec: ThemeSpec = get_theme(self._theme_name)

    def _configure_window_frame(self) -> None:
        self.setWindowTitle("Fractal Studio")
        self.resize(1500, 940)

    def _bootstrap_startup(self):
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

    def _finalize_startup(self, startup) -> None:
        self.setCentralWidget(self._build_layout())
        self._theme_controller.refresh_dynamic_widgets(self._hover_panel, self._fav_rows)
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
        layout.addWidget(self._sections.build_header(self.backend_profile, self._open_settings))
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
            dialog_factory=lambda theme, parent: AppearanceSettingsDialog(theme, parent),
            application=QApplication.instance(),
            refresh_dynamic_widgets=lambda: self._theme_controller.refresh_dynamic_widgets(
                self._hover_panel,
                self._fav_rows,
            ),
        )

    def _set_custom_export_row_visible(self, visible: bool) -> None:
        if self._custom_width_box is None:
            return
        custom_row = self._custom_width_box.parentWidget()
        if custom_row is not None:
            custom_row.setVisible(visible)

    def _on_export_preset_changed(self, index: int) -> None:
        self._export_panel.on_export_preset_changed(
            index=index,
            export_presets=self._export_presets,
            custom_width_box=self._custom_width_box,
            custom_height_box=self._custom_height_box,
            set_custom_row_visible=self._set_custom_export_row_visible,
        )

    def _refresh_export_presets(self) -> None:
        self._export_presets = self._export_panel.refresh_export_presets(
            aspect_ratio_mode=self._aspect_ratio_mode,
            export_combo=self._export_combo,
            current_presets=self._export_presets,
            on_export_preset_changed=self._on_export_preset_changed,
        )

    def _apply_aspect_ratio_mode(self, mode: str, update_combo: bool = True) -> None:
        self._aspect_ratio_mode = mode
        self._aspect_ratio_mode = self._export_panel.apply_aspect_ratio_mode(
            mode=mode,
            viewport=self.viewport,
            aspect_ratio_combo=self._aspect_ratio_combo,
            refresh_export_presets=self._refresh_export_presets,
            update_combo=update_combo,
        )

    def _select_favorite_row(self, row: FavoriteThumbnailRow) -> None:
        self._selected_row = self._favorites_panel.select_row(self._selected_row, row)

    def _activate_favorite_row(self, row: FavoriteThumbnailRow) -> None:
        self._favorites_workflow.load_favorite_row(
            row=row,
            favorites=self._favorites,
            rows=self._fav_rows,
            viewport=self.viewport,
            params_panel=self.params_panel,
            editor=self.editor,
            preview_palette=self.preview_palette,
            apply_aspect_ratio_mode=self._apply_aspect_ratio_mode,
            select_row=self._select_favorite_row,
            show_status=self.statusBar().showMessage,
        )

    def _add_favorite_row(self, fav: dict) -> None:
        row = self._favorites_panel.build_row_with_callbacks(
            favorite=fav,
            owner=self,
            hover_panel=self._hover_panel,
            on_select_row=lambda mw, row: mw._select_favorite_row(row),
            on_activate_row=lambda mw, row: mw._activate_favorite_row(row),
            row_factory=FavoriteThumbnailRow,
            decode_thumbnail=decode_thumbnail,
            placeholder_pixmap=placeholder_pixmap,
        )
        self._favorites_panel.append_row(row, self._fav_rows, self._fav_scroll_layout)


