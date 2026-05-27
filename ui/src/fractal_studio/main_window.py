from __future__ import annotations

import base64
import datetime
import weakref
from pathlib import Path

_FAVORITES_PATH = Path.home() / ".fractal_studio" / "favorites.json"
_SETTINGS_PATH = Path.home() / ".fractal_studio" / "settings.json"

from PySide6.QtCore import QBuffer, QByteArray, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QToolButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from fractal_studio.backend import BackendProfile, load_backend
from fractal_studio.editor import ColorCubeEditor, PalettePreviewWidget
from fractal_studio.export_service import ExportService
from fractal_studio.favorite_hover_presenter import FavoriteHoverPresenter
from fractal_studio.favorite_row_style_presenter import FavoriteRowStylePresenter
from fractal_studio.favorites_controller import FavoritesController
from fractal_studio.main_window_controller import MainWindowController
from fractal_studio.main_window_sections import MainWindowSections
from fractal_studio.palette_service import PaletteWorkflowService
from fractal_studio.persistence import FavoritesRepository, SettingsRepository
from fractal_studio.settings_service import SettingsWorkflowService
from fractal_studio.state import (
    UiSettings,
    ViewportState,
)
from fractal_studio.theme import ThemeSpec, apply_theme, get_theme
from fractal_studio.theme_controller import ThemeController
from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget


class CustomResolutionDialog(QDialog):
    def __init__(self, default_width: int = 1920, default_height: int = 1080, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Custom Resolution")
        self._width_box = QSpinBox()
        self._width_box.setRange(64, 16384)
        self._width_box.setValue(default_width)
        self._height_box = QSpinBox()
        self._height_box.setRange(64, 16384)
        self._height_box.setValue(default_height)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout()
        layout.addRow("Width:", self._width_box)
        layout.addRow("Height:", self._height_box)
        layout.addRow(buttons)
        self.setLayout(layout)

    def values(self) -> tuple[int, int]:
        return self._width_box.value(), self._height_box.value()


class FavoriteThumbnailRow(QWidget):
    def __init__(
        self,
        pixmap: QPixmap,
        fav: dict,
        hover_panel: QLabel,
        on_select,
        on_activate=None,
        hover_presenter: FavoriteHoverPresenter | None = None,
        style_presenter: FavoriteRowStylePresenter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._fav = fav
        self._hover_panel = hover_panel
        self._hover_presenter = hover_presenter or FavoriteHoverPresenter()
        self._style_presenter = style_presenter or FavoriteRowStylePresenter()
        self._on_select = on_select
        self._on_activate = on_activate if on_activate is not None else on_select
        self._selected = False
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout()
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(8)

        self._thumb_label = QLabel()
        self._thumb_label.setObjectName("favoriteThumb")
        self._thumb_label.setFixedSize(48, 36)
        self._thumb_label.setPixmap(
            pixmap.scaled(48, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )

        self._name_label = QLabel(fav["name"])
        self._name_label.setObjectName("favoriteName")
        self._name_label.setMinimumWidth(0)
        self._name_label.setWordWrap(False)

        # Let the row receive hover/click events even when the cursor is over child labels.
        self._thumb_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout.addWidget(self._thumb_label)
        layout.addWidget(self._name_label, 1)
        self.setLayout(layout)
        self._thumb_label.setStyleSheet("border: 2px solid transparent; border-radius: 3px;")
        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_visual_state()

    def _set_hovered(self, hovered: bool) -> None:
        self._hovered = hovered
        self._apply_visual_state()

    def _apply_visual_state(self) -> None:
        self._style_presenter.apply_visual_state(
            self,
            self._thumb_label,
            self._name_label,
            selected=self._selected,
            hovered=self._hovered,
        )

    def mousePressEvent(self, event) -> None:
        self._on_select(self)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self._on_select(self)
        self._on_activate(self)
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event) -> None:
        self._set_hovered(True)
        self._hover_presenter.show_for_row(self, self._hover_panel, self._fav)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_hovered(False)
        self._hover_presenter.hide(self._hover_panel)
        super().leaveEvent(event)


class PlaceholderPanel(QGroupBox):
    def __init__(self, title: str, lines: list[str]) -> None:
        super().__init__(title)
        layout = QVBoxLayout()
        for line in lines:
            label = QLabel(line)
            label.setWordWrap(True)
            layout.addWidget(label)
        layout.addStretch()
        self.setLayout(layout)


class AppearanceSettingsDialog(QDialog):
    theme_preview_requested = Signal(str)

    def __init__(self, current_theme: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setObjectName("settingsDialog")
        self.resize(860, 520)
        self._initial_theme = current_theme
        self._selected_theme = current_theme

        root = QWidget()
        root.setObjectName("settingsRoot")
        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("settingsSidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(14, 16, 14, 16)
        sidebar_layout.setSpacing(8)

        sidebar_title = QLabel("Preferences")
        sidebar_title.setObjectName("settingsSidebarTitle")
        sidebar_layout.addWidget(sidebar_title)

        appearance_tab = QPushButton("Appearance")
        appearance_tab.setObjectName("settingsNavActive")
        appearance_tab.setEnabled(False)
        sidebar_layout.addWidget(appearance_tab)

        for label in ("Rendering", "Export", "Behavior", "Advanced"):
            tab = QPushButton(label)
            tab.setObjectName("settingsNavDisabled")
            tab.setEnabled(False)
            sidebar_layout.addWidget(tab)

        sidebar_layout.addStretch()
        sidebar.setLayout(sidebar_layout)

        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 18, 20, 18)
        content_layout.setSpacing(14)

        title = QLabel("Appearance")
        title.setObjectName("settingsHeading")
        subtitle = QLabel("Choose a UI theme. Select a theme to preview it, then click Apply to keep it.")
        subtitle.setObjectName("settingsSubtitle")

        section_label = QLabel("Theme")
        section_label.setObjectName("settingsSectionTitle")

        theme_card = QFrame()
        theme_card.setObjectName("settingsThemeCard")
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        self._light = QRadioButton("Light")
        self._dark = QRadioButton("Dark")
        self._sepia = QRadioButton("Sepia")
        self._buttons = {
            "light": self._light,
            "dark": self._dark,
            "sepia": self._sepia,
        }
        self._buttons.get(current_theme, self._light).setChecked(True)

        for key, button in self._buttons.items():
            button.setObjectName("settingsThemeOption")
            button.toggled.connect(lambda checked, name=key: self._on_theme_toggled(name, checked))
            card_layout.addWidget(button)

        theme_card.setLayout(card_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close
        )
        buttons.setObjectName("settingsButtons")
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if apply_button is not None:
            apply_button.clicked.connect(self.accept)
        if close_button is not None:
            close_button.clicked.connect(self.reject)

        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)
        content_layout.addWidget(section_label)
        content_layout.addWidget(theme_card)
        content_layout.addStretch()
        content_layout.addWidget(buttons)
        content.setLayout(content_layout)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)
        root.setLayout(root_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(root)
        self.setLayout(layout)

    def _on_theme_toggled(self, theme_name: str, checked: bool) -> None:
        if checked:
            self._selected_theme = theme_name
            self.theme_preview_requested.emit(theme_name)

    def selected_theme(self) -> str:
        return self._selected_theme


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._favorites_repo = FavoritesRepository(_FAVORITES_PATH)
        self._settings_repo = SettingsRepository(_SETTINGS_PATH)
        self._settings_service = SettingsWorkflowService()
        self._favorites_controller = FavoritesController()
        self._sections = MainWindowSections(self)
        self._theme_controller = ThemeController()
        self._favorite_hover_presenter = FavoriteHoverPresenter()
        self.backend = load_backend()
        self._export_service = ExportService(self.backend)
        self._palette_service = PaletteWorkflowService()
        self._controller = MainWindowController(self._export_service, self._favorites_controller)
        self.backend_loaded = self.backend.available
        self.backend_profile = self.backend.profile()
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

        self.setWindowTitle("Fractal Studio")
        self.resize(1500, 940)

        settings = self._settings_repo.load()
        self._theme_name = settings.settings.theme
        self._theme_spec = apply_theme(QApplication.instance(), self._theme_name)

        self._hover_panel = QLabel(self)
        self._hover_panel.setObjectName("hoverPanel")
        self._hover_panel.hide()

        self.setCentralWidget(self._build_layout())
        self._apply_theme_to_dynamic_widgets()
        status_message = (
            self._settings_service.startup_message(settings)
            or self._settings_service.status_message(self.backend_loaded, settings.source)
        )
        status_message = self._settings_service.append_diagnostics(
            status_message,
            [settings.diagnostic, self._favorites_repo.last_load_diagnostic],
        )
        self.statusBar().showMessage(status_message)

    def _build_layout(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._sections.build_workspace())
        splitter.addWidget(self._sections.build_sidebar())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1200, 300])

        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self._sections.build_header(self.backend_profile, self._open_settings))
        layout.addWidget(splitter)
        container.setLayout(layout)
        return container

    def _refresh_export_presets(self) -> None:
        self._export_presets = self._controller.refresh_export_presets(
            aspect_ratio_mode=self._aspect_ratio_mode,
            export_combo=self._export_combo,
            current_presets=self._export_presets,
            on_export_preset_changed=self._on_export_preset_changed,
        )

    def _apply_aspect_ratio_mode(self, mode: str, update_combo: bool = True) -> None:
        if mode not in ("square", "portrait", "landscape"):
            mode = "square"
        # Ensure refresh callbacks observe the newly selected mode.
        self._aspect_ratio_mode = mode
        self._aspect_ratio_mode = self._controller.apply_aspect_ratio_mode(
            mode=mode,
            viewport=self.viewport,
            aspect_ratio_combo=self._aspect_ratio_combo,
            refresh_export_presets=self._refresh_export_presets,
            update_combo=update_combo,
        )

    def _on_aspect_ratio_changed(self, index: int) -> None:
        mode = self._controller.aspect_mode_from_index(index)
        self._apply_aspect_ratio_mode(mode, update_combo=False)

    def _on_export_preset_changed(self, index: int) -> None:
        if self._custom_width_box is None or self._custom_height_box is None:
            return
        is_custom = self._controller.should_show_custom_size(index, len(self._export_presets))
        self._custom_width_box.parentWidget().setVisible(is_custom)

    def _on_export_clicked(self) -> None:
        if self._export_combo is None:
            return

        self._controller.on_export_clicked(
            export_presets=self._export_presets,
            index=self._export_combo.currentIndex(),
            custom_width_box=self._custom_width_box,
            custom_height_box=self._custom_height_box,
            set_custom_size=lambda w, h: setattr(self, "_custom_width", w) or setattr(self, "_custom_height", h),
            export_callback=self._export_render,
        )

    def _export_render(self, width: int, height: int) -> None:
        self._controller.export_render(
            self,
            self.viewport,
            width,
            height,
            self.statusBar().showMessage,
        )

    def _add_favorite_row(self, fav: dict) -> None:
        if "thumbnail" in fav:
            try:
                pixmap = MainWindow._decode_thumbnail(fav["thumbnail"])
                if pixmap.isNull():
                    pixmap = MainWindow._placeholder_pixmap()
            except Exception:
                pixmap = MainWindow._placeholder_pixmap()
        else:
            pixmap = MainWindow._placeholder_pixmap()
        # Use a weakref to break the MainWindow ↔ FavoriteThumbnailRow reference cycle
        # so CPython's cyclic GC doesn't finalize Rust-backed objects at unsafe times.
        weak_self = weakref.ref(self)

        def on_select(row: FavoriteThumbnailRow) -> None:
            mw = weak_self()
            if mw is not None:
                mw._on_row_selected(row)

        def on_activate(row: FavoriteThumbnailRow) -> None:
            mw = weak_self()
            if mw is not None:
                mw._load_favorite_row(row)

        row = FavoriteThumbnailRow(
            pixmap,
            fav,
            self._hover_panel,
            on_select,
            on_activate,
            hover_presenter=self._favorite_hover_presenter,
        )
        self._fav_rows.append(row)
        # Insert before the trailing stretch (always last item)
        self._fav_scroll_layout.insertWidget(len(self._fav_rows) - 1, row)

    def _on_row_selected(self, row: FavoriteThumbnailRow) -> None:
        if self._selected_row is not None:
            self._selected_row.set_selected(False)
        self._selected_row = row
        row.set_selected(True)

    def _save_favorite(self) -> None:
        if self.viewport is None:
            return
        self._favorites_controller.save_favorite(
            viewport=self.viewport,
            editor=self.editor,
            aspect_ratio_mode=self._aspect_ratio_mode,
            favorites=self._favorites,
            build_name=self._build_favorite_name,
            capture_thumbnail=self._capture_thumbnail,
            add_favorite=self._favorites.append,
            add_row=self._add_favorite_row,
            persist=lambda: self._favorites_controller.persist_favorites(self._favorites, self._favorites_repo.save),
            show_status=self.statusBar().showMessage,
        )

    def _build_favorite_name(self, state: ViewportState) -> str:
        existing_names = {fav.get("name", "") for fav in self._favorites}
        return self._favorites_controller.build_favorite_name(state, existing_names, datetime.datetime.now)

    def _load_favorite(self) -> None:
        if self.viewport is None or self.params_panel is None or self._selected_row is None:
            return
        self._load_favorite_row(self._selected_row)

    def _load_favorite_row(self, row: FavoriteThumbnailRow) -> None:
        self._favorites_controller.load_favorite_row(
            row=row,
            favorites=self._favorites,
            rows=self._fav_rows,
            viewport=self.viewport,
            params_panel=self.params_panel,
            editor=self.editor,
            preview_palette=self.preview_palette,
            apply_aspect_ratio_mode=self._apply_aspect_ratio_mode,
            select_row=self._on_row_selected,
            show_status=self.statusBar().showMessage,
        )

    def _delete_favorite(self) -> None:
        if self._selected_row is None:
            return
        idx = self._fav_rows.index(self._selected_row)
        self._favorites.pop(idx)
        row = self._fav_rows.pop(idx)
        self._fav_scroll_layout.removeWidget(row)
        row.deleteLater()
        self._selected_row = None
        self._favorites_controller.persist_favorites(self._favorites, self._favorites_repo.save)

    def _update_control_summary(self, control_points: list[tuple[int, int, int]]) -> None:
        if self.point_summary is None:
            return

        self.point_summary.setText(f"{len(control_points)} control points")

    def _update_palette_previews(self, palette: list[tuple[int, int, int]]) -> None:
        self._favorites_controller.update_palette_previews(
            palette=palette,
            editor=self.editor,
            backend=self.backend,
            legacy_palette_size=self.backend_profile.legacy_palette_size,
            preview_palette=self.preview_palette,
            preview_legacy=self.preview_legacy,
            palette_summary=self.palette_summary,
        )

    def _save_palette_json(self) -> None:
        if self.editor is None:
            return

        self._palette_service.save_palette_json(
            parent=self,
            backend=self.backend,
            control_points=self.editor.control_points,
            palette_size=self.backend_profile.palette_size,
            set_status=self.statusBar().showMessage,
        )

    def _load_palette_json(self) -> None:
        if self.editor is None:
            return

        self._palette_service.load_palette_json(
            parent=self,
            backend=self.backend,
            set_control_points=self.editor.set_control_points,
            set_status=self.statusBar().showMessage,
        )

    def _export_legacy_map(self) -> None:
        if self.editor is None:
            return

        self._palette_service.export_legacy_map(
            parent=self,
            backend=self.backend,
            control_points=self.editor.control_points,
            legacy_palette_size=self.backend_profile.legacy_palette_size,
            set_status=self.statusBar().showMessage,
        )

    def _open_settings(self) -> None:
        self._controller.open_settings_dialog(
            parent=self,
            current_theme=self._theme_name,
            dialog_factory=lambda theme, parent: AppearanceSettingsDialog(theme, parent),
            apply_theme_name=self._apply_theme_name,
        )

    def _apply_theme_name(self, theme_name: str, persist: bool) -> None:
        self._theme_name = self._settings_service.apply_theme_name(
            theme_name=theme_name,
            persist=persist,
            current_theme=self._theme_name,
            apply_theme_to_app=lambda name: setattr(
                self,
                "_theme_spec",
                self._theme_controller.apply_theme(QApplication.instance(), name),
            ),
            persist_theme=lambda name: self._settings_repo.save(UiSettings(theme=name)),
        )
        self._theme_controller.refresh_dynamic_widgets(self._hover_panel, self._fav_rows)

    def _apply_theme_to_dynamic_widgets(self) -> None:
        self._theme_controller.refresh_dynamic_widgets(self._hover_panel, self._fav_rows)

    @staticmethod
    def _encode_pixmap(pixmap: QPixmap) -> str:
        scaled = pixmap.scaled(
            96, 72,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        scaled.toImage().save(buf, "PNG")
        buf.close()
        return base64.b64encode(bytes(ba)).decode()

    @staticmethod
    def _decode_thumbnail(b64: str) -> QPixmap:
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(b64))
        return pixmap

    @staticmethod
    def _placeholder_pixmap() -> QPixmap:
        pixmap = QPixmap(48, 36)
        pixmap.fill(QColor("#313244"))
        return pixmap

    def _capture_thumbnail(self) -> str:
        return MainWindow._encode_pixmap(self.viewport.grab())

    def _backend_state_text(self) -> str:
        return (
            "Rust extension loaded."
            if self.backend_loaded and self.backend.available
            else "Rust extension not loaded. Build fractal_core to enable the editor."
        )

